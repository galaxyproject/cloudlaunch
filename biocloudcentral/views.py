"""Base views.
"""
import copy
import logging

import yaml

from django.http import HttpResponse
from django.template import RequestContext
from django.utils import simplejson
from django.shortcuts import render, redirect

from biocloudcentral import forms
from biocloudcentral import models
from bioblend.cloudman.launch import CloudManLauncher

log = logging.getLogger(__name__)

# ## Landing page with redirects

def home(request):
    launch_url = request.build_absolute_uri("/launch")
    if launch_url.startswith(("http://127.0.0.1", "http://localhost")):
        return redirect("/launch")
    else:
        return redirect("https://biocloudcentral.herokuapp.com/launch")

# ## CloudMan launch and configuration entry details
def launch(request):
    """Configure and launch CloudBioLinux and CloudMan servers.
    """
    if request.method == "POST":
        form = forms.CloudManForm(request.POST)
        if form.is_valid():
            request.session["ec2data"] = form.cleaned_data
            request.session["ec2data"]['cloud_name'] = form.cleaned_data['cloud'].name
            request.session["ec2data"]['cloud_type'] = form.cleaned_data['cloud'].cloud_type
            # Temp code (Jan 2013) - until Queensland Cloud is operational allow only
            # test account to launch instances
            if request.session["ec2data"]['cloud_name'] == 'Qld Test Cloud' and \
                form.cleaned_data.get('access_key', '') != 'b2b2057ab3644f508ff6ff20d914f74e':
                response = {'error': "*You cannot use {0} cloud yet; it is available only for " \
                    "testing at the moment.*".format(request.session["ec2data"]['cloud_name'])}
            else:
                response = runinstance(request)
            if not response['error']:
                return redirect("/monitor")
            else:
                form.non_field_errors = "A problem starting your instance. "\
                                        "Check the {0} cloud's console: {1}"\
                                        .format(form.cleaned_data['cloud'].name,
                                                response['error'])
    else:
        # Select the first item in the clouds dropdown, thus potentially eliminating
        # that click for the most commonly used cloud. This does assume the most used
        # cloud is the first in the DB and that such an entry exists in the first place
        form = forms.CloudManForm(initial={'cloud': 1})
    return render(request, "launch.html", {"form": form}, context_instance=RequestContext(request))

def monitor(request):
    """Monitor a launch request and return offline files for console re-runs.
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
        request.session['ec2data']['instance_id'] = rs.instances[0].id
        request.session['ec2data']['public_ip'] = rs.instances[0].ip_address  # public_dns_name
        request.session['ec2data']['image_id'] = rs.instances[0].image_id
        request.session['ec2data']['kp_name'] = response['kp_name']
        request.session['ec2data']['kp_material'] = response['kp_material']
        request.session['ec2data']['sg_name'] = response['sg_names'][0]

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
    form = request.session["ec2data"]
    cml = CloudManLauncher(form["access_key"], form["secret_key"], form['cloud'])
    state = cml.get_status(form["instance_id"])
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
                    instance_types.append((it.tech_name, \
                        "{0} ({1})".format(it.pretty_name, it.description)))
                # Get Image IDs for the given cloud
                iids = models.Image.objects.filter(cloud=cloud_id)
                for iid in iids:
                    image_ids.append((iid.pk, \
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
            cloud_id = request.POST.get('cloud_id', '')
            a_key = request.POST.get('a_key', '')
            s_key = request.POST.get('s_key', '')
            inst_type = request.POST.get('instance_type', '')
            placements = []
            if cloud_id != '' and a_key != '' and s_key != '':
                # Needed to get the cloud connection
                cloud = models.Cloud.objects.get(pk=cloud_id)
                cml = CloudManLauncher(a_key, s_key, cloud)
                placements = cml._find_placements(cml.ec2_conn, inst_type, cloud.cloud_type)
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
        log.debug("Got here 1")
        if msg.startswith("EC2ResponseError"):
            try:
                msg = msg.split("<Message>")[-1].split("</Message>")[0]
                # handle standard error cases
                if msg.startswith("The request signature we calculated does not match"):
                    msg = "Access and secret keys not accepted"
                    log.debug("Got here 2")
            except Exception, inner:
                log.debug("Got here 3")
                msg = str(e) + " inner is: " + str(inner)
                log.debug("Got here 4")
        state = {"error": msg, "placements": []}
        log.debug("Got here 5")
    return HttpResponse(simplejson.dumps(state), mimetype="application/json")

