"""Base views.
"""
import copy
import logging
import yaml
from random import randint

from celery.result import AsyncResult
from celery.task.control import revoke

from django.http import HttpResponse
from django.template import RequestContext
from django.utils import simplejson
from django.shortcuts import render, redirect

from biocloudcentral import forms
from biocloudcentral import models
from biocloudcentral import tasks
from biocloudcentral.settings import REDIRECT_BASE
from bioblend.cloudman.launch import CloudManLauncher


log = logging.getLogger(__name__)

# ## Landing page with redirects


def home(request):
    launch_url = request.build_absolute_uri("/launch")
    if launch_url.startswith(("http://127.0.0.1", "http://localhost")) or not REDIRECT_BASE:
        return redirect("/launch")
    else:
        redirect_base = REDIRECT_BASE
        if not redirect_base.endswith("/"):
            redirect_base = "%s/" % redirect_base
        return redirect("%slaunch" % redirect_base)


def launch(request):
    """
    Initiate launching of an instance. Given an empty request, render the
    ``launch`` page. Given a ``POST`` request, initiate a background task to
    launch an instance and return JSON with the task ID and ``ready`` status sttribute
    set to ``false``.
    """
    if request.method == "POST":
        data = {'task_id': '', 'ready': '', 'error': ''}
        form = forms.CloudManForm(data=request.POST)
        if form.is_valid() and request.is_ajax:
            request.session["ec2data"] = form.cleaned_data
            request.session["ec2data"]['cloud_name'] = form.cleaned_data['cloud'].name
            request.session["ec2data"]['cloud_type'] = form.cleaned_data['cloud'].cloud_type
            # Initiate a background task now
            form = request.session["ec2data"]
            r = tasks.run_instance.delay(form)
            data['task_id'] = r.id
            data['ready'] = False
        else:
            # FIXME: make sure form errors are captured and propagaed back
            data['error'] = dict([(k, [unicode(e) for e in v]) for k, v in form.errors.items()])
        return HttpResponse(simplejson.dumps(data), mimetype="application/json")
    else:
        # Select the first item in the clouds dropdown, thus potentially eliminating
        # that click for the most commonly used cloud. This does assume the most used
        # cloud is the first in the DB and that such an entry exists in the first place
        form = forms.CloudManForm(initial={'cloud': 1})
    return render(request, "launch.html", {"form": form}, context_instance=RequestContext(request))


def launch_status(request):
    """
    Given a task ID of a launch process/task, check if the task has completed.
    Return a JSON object with the following keys: ``task_id``, ``ready``, and
    ``error``
    """
    task_id = request.POST.get('task_id', '')
    r = {'task_id': '', 'ready': '', 'error': ''}
    if task_id:
        r['task_id'] = task_id
        result = AsyncResult(task_id)
        r['ready'] = result.ready()
        if r['ready']:  # The task completed; let's get the outcome
            # Set session data based on the task result
            # TODO: this should always return JSON and not mess with the session
            #       Then, need to redo how monitor page is displayed...
            response = result.get()
            if response.get("error", ""):
                r['error'] = response['error']
            else:
                request.session['ec2data']['cluster_name'] = response['cluster_name']
                request.session['ec2data']['instance_id'] = response['instance_id']
                request.session['ec2data']['public_ip'] = response['instance_ip']
                request.session['ec2data']['image_id'] = response['image_id']
                request.session['ec2data']['kp_name'] = response['kp_name']
                request.session['ec2data']['kp_material'] = response['kp_material']
                request.session['ec2data']['sg_name'] = response['sg_names'][0]
                request.session['ec2data']['password'] = response['password']
                # Add an entry to the Usage table now
                try:
                    u = models.Usage(cloud_name=response["cloud_name"],
                                     cloud_type=response["cloud_type"],
                                     image_id=response['image_id'],
                                     instance_type=response['instance_type'],
                                     user_id=response["access_key"])
                    u.save()
                except Exception, e:
                    log.debug("Trouble saving Usage data: {0}".format(e))
    return HttpResponse(simplejson.dumps(r), mimetype="application/json")


def monitor(request):
    """
    Monitor a launch request and return offline files for console re-runs.
    """
    return render(request, "monitor.html", context_instance=RequestContext(request))


def runinstance(request):
    """Run a CloudBioLinux/CloudMan instance with current session credentials.
    """
    form = request.session["ec2data"]

    # Handle extra_user_data
    extra_user_data = form['extra_user_data']
    if extra_user_data:
        for key, value in yaml.load(extra_user_data).iteritems():
            form[key] = value
    del form['extra_user_data']

    rs = None
    instance_type = form['instance_type']
    # Create cloudman connection with provided creds
    cml = CloudManLauncher(form["access_key"], form["secret_key"], form['cloud'])
    form["freenxpass"] = form["password"]
    if form['image_id']:
        image = models.Image.objects.get(pk=form['image_id'])
    else:
        try:
            image = models.Image.objects.get(cloud=form['cloud'], default=True)
        except models.Image.DoesNotExist:
            log.error("Cannot find an image to launch for cloud {0}".format(form['cloud']))
            return False
    # Compose kwargs from form data making sure the named arguments are not included
    kwargs = copy.deepcopy(form)
    for key in form.iterkeys():
        if key in ['cluster_name', 'image_id', 'instance_type', 'password',
                   'placement', 'access_key', 'secret_key', 'cloud']:
            del kwargs[key]
    response = cml.launch(cluster_name=form['cluster_name'],
                        image_id=image.image_id,
                        instance_type=instance_type,
                        password=form["password"],
                        kernel_id=image.kernel_id if image.kernel_id != '' else None,
                        ramdisk_id=image.ramdisk_id if image.ramdisk_id != '' else None,
                        placement=form['placement'],
                        **kwargs)
    if response["error"]:
        return response
    elif response["rs"]:
        rs = response["rs"]
        request.session['ec2data']['cluster_name'] = form['cluster_name']
        request.session['ec2data']['instance_id'] = rs.instances[0].id
        request.session['ec2data']['public_ip'] = rs.instances[0].ip_address  # public_dns_name
        request.session['ec2data']['image_id'] = rs.instances[0].image_id
        request.session['ec2data']['kp_name'] = response['kp_name']
        request.session['ec2data']['kp_material'] = response['kp_material']
        request.session['ec2data']['sg_name'] = response['sg_names'][0]
        request.session['ec2data']['password'] = form['password']

        # Add an entry to the Usage table
        try:
            u = models.Usage(cloud_name=form["cloud_name"],
                             cloud_type=form["cloud_type"],
                             image_id=image.image_id,
                             instance_type=instance_type,
                             user_id=form["access_key"])
            u.save()
        except Exception, e:
            log.debug("Trouble saving Usage data: {0}".format(e))
    return response


def userdata(request):
    """Provide file download of user-data to re-start an instance.
    """
    ec2data = request.session["ec2data"]
    response = HttpResponse(mimetype='text/plain')
    response['Content-Disposition'] = 'attachment; filename={cluster_name}-userdata.txt'.format(
        **ec2data)
    form = request.session["ec2data"]
    cml = CloudManLauncher(form["access_key"], form["secret_key"], form['cloud'])
    ud = cml._compose_user_data(ec2data)
    response.write(ud)
    return response


def keypair(request):
    ec2data = request.session["ec2data"]
    response = HttpResponse(mimetype='text/plain')
    response['Content-Disposition'] = 'attachment; filename={kp_name}-key.pem'.format(
        **ec2data)
    response.write(ec2data['kp_material'])
    return response


def instancestate(request):
    task_id = request.POST.get('task_id', None)
    instance_state = request.POST.get('instance_state', 'pending')  # Preserve current state
    state = {'task_id': None, 'instance_state': instance_state}  # Reset info to be sent
    if task_id:
        # If we have a running task, check on instance state
        result = AsyncResult(task_id)
        if result.ready():
            state = result.get()
            state['task_id'] = None  # Reset but make sure it exists
        else:
            # If task not ready, send back the task_id
            state['task_id'] = task_id
    elif 'ec2data' in request.session:
        # We have no task ID, so start a task to get instance state
        form = request.session["ec2data"]
        cloud = form['cloud']
        a_key = form["access_key"]
        s_key = form["secret_key"]
        instance_id = form["instance_id"]
        r = tasks.instance_state.delay(cloud, a_key, s_key, instance_id)
        state['task_id'] = r.id
    else:
        state = {'instance_state': 'Not available'}
    return HttpResponse(simplejson.dumps(state), mimetype="application/json")


def dynamicfields(request):
    if request.is_ajax():
        if request.method == 'POST':
            cloud_id = request.POST.get('cloud_id', '')
            instance_types, image_ids = [], []
            if cloud_id != '':
                # Get instance types for the given cloud
                its = models.InstanceType.objects.filter(cloud=cloud_id)
                for it in its:
                    instance_types.append((it.tech_name,
                        "{0} ({1})".format(it.pretty_name, it.description)))
                # Get Image IDs for the given cloud
                iids = models.Image.objects.filter(cloud=cloud_id)
                for iid in iids:
                    image_ids.append((iid.pk,
                        "{0} ({1}){default}".format(iid.description, iid.image_id,
                        default="*" if iid.default is True else '')))
            state = {'instance_types': instance_types,
                     'image_ids': image_ids}
        else:
            log.error("Not a POST request")
    else:
        log.error("No XHR")
    return HttpResponse(simplejson.dumps(state), mimetype="application/json")


def _get_placement_inner(request):
    if request.is_ajax():
        if request.method == 'POST':
            cluster_name = request.POST.get('cluster_name', '')
            cloud_id = request.POST.get('cloud_id', '')
            a_key = request.POST.get('a_key', '')
            s_key = request.POST.get('s_key', '')
            inst_type = request.POST.get('instance_type', '')
            placements = []
            if cloud_id != '' and a_key != '' and s_key != '':
                # Needed to get the cloud connection
                cloud = models.Cloud.objects.get(pk=cloud_id)
                cml = CloudManLauncher(a_key, s_key, cloud)
                placements = cml.find_placements(cml.ec2_conn, inst_type,
                    cloud.cloud_type, cluster_name)
                return {'placements': placements}
        else:
            log.error("Not a POST request")
    else:
        log.error("No XHR")
    return {"error": "Please specify access and secret keys", "placements": []}


def get_placements(request):
    try:
        state = _get_placement_inner(request)
    except Exception, e:
        log.exception("Problem retrieving availability zones")
        msg = str(e)
        if msg.startswith("EC2ResponseError"):
            msg = msg.split("<Message>")[-1].split("</Message>")[0]
            # handle standard error cases
            if msg.startswith("The request signature we calculated does not match"):
                msg = "Access and secret keys not accepted"
        state = {"error": msg, "placements": []}
    return HttpResponse(simplejson.dumps(state), mimetype="application/json")


def fetch_clusters(request):
    """
    Intiate retrieval of a list of clusters associated with a given account on
    a given cloud. Returns a JSON with a ``task_id`` key to be used to get the
    status and the actual list of clusters (via ``fetch_clusters_status`` method).
    """
    cloud_id = request.POST.get('cloud_id', '')
    a_key = request.POST.get('a_key', '')
    s_key = request.POST.get('s_key', '')
    cloud = models.Cloud.objects.get(pk=cloud_id)
    # Queue the task and return the task ID
    r = tasks.fetch_clusters.delay(cloud, a_key, s_key)
    task_id = {'task_id': r.id}
    return HttpResponse(simplejson.dumps(task_id), mimetype="application/json")


def update_clusters(request):
    """
    Given a task ID as part of the ``request`` (as ``request_id``), check on the
    status of a job retrieving clusters' persistent data. Return a JSON with the
    following fields:
        ``task_id``: return the job request ID
        ``ready``: ``True`` if the job has completed; ``False`` otherwise
        ``clusters_list``: a list of clusters' persistent data (if the job
            has completed) or an empty list otherwise
    """
    task_id = request.POST.get('task_id', '')
    result = AsyncResult(task_id)
    fetching_data_text_list = ['Fetching data... please wait', 'Fetching data...',
        'Still fetching data...', 'Hopefully done soon!']
    fdt = fetching_data_text_list[randint(0, len(fetching_data_text_list) - 1)]
    r = {'task_id': task_id,
         'ready': result.ready(),
         'clusters_list': [],
         'wait_text': fdt}
    if result.ready():
        r['clusters_list'] = result.get()
    return HttpResponse(simplejson.dumps(r), mimetype="application/json")


def revoke_fetch_clusters(request):
    """
    Revoke a task with ``task_id`` that's to be provided as part of the ``request``.
    When a worker receives a revoke request it will skip executing the task. In
    case a task is executing, it will kill it.

    .. Note::
      Revoking a task works only with a *proper* messaging backend; it does not
      work with Kombu.
    """
    task_id = request.POST.get('task_id', '')
    revoke(task_id, terminate=True, signal='SIGKILL')
    # Always report that a task has been revoked
    return HttpResponse(simplejson.dumps({'revoked': True}), mimetype="application/json")
