"""Base views.
"""
import logging

from django.http import HttpResponse
from django.template import RequestContext
from django.utils import simplejson
from django.shortcuts import render, redirect

from boto.exception import EC2ResponseError

from biocloudcentral import forms
from biocloudcentral import models
from biocloudcentral.amazon.launch import (connect_ec2, instance_state,
                                           create_cm_security_group,
                                           create_key_pair, run_instance,
                                           _compose_user_data, _find_placements)

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
            ec2_error = None
            try:
                # Create security group & key pair used when starting an instance
                ec2_conn = connect_ec2(form.cleaned_data['access_key'],
                                       form.cleaned_data['secret_key'],
                                       form.cleaned_data['cloud'])
                sg_name = create_cm_security_group(ec2_conn, form.cleaned_data['cloud'])
                kp_name, kp_material = create_key_pair(ec2_conn)
            except EC2ResponseError, err:
                ec2_error = err.error_message
            # associate form data with session for starting instance
            # and supplying download files
            if ec2_error is None:
                form.cleaned_data["kp_name"] = kp_name
                form.cleaned_data["kp_material"] = kp_material
                form.cleaned_data["sg_name"] = sg_name
                form.cleaned_data["cloud_type"] = form.cleaned_data['cloud'].cloud_type
                form.cleaned_data["cloud_name"] = form.cleaned_data['cloud'].name
                request.session["ec2data"] = form.cleaned_data
                error_msg = runinstance(request)
                if error_msg is None:
                    return redirect("/monitor")
                else:
                    form.non_field_errors = "A problem starting your instance. " \
                                            "Check the {0} cloud's console: {1}"\
                                            .format(form.cleaned_data['cloud'].name,
                                                    error_msg)
            else:
                form.non_field_errors = ec2_error
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
    rs = None
    instance_type = form['instance_type']
    # Create EC2 connection with provided creds
    ec2_conn = connect_ec2(form["access_key"], form["secret_key"], form['cloud'])
    form["freenxpass"] = form["password"]
    if form['image_id']:
        image = models.Image.objects.get(pk=form['image_id'])
    else:
        try:
            image = models.Image.objects.get(cloud=form['cloud'], default=True)
        except models.Image.DoesNotExist:
            log.error("Cannot find an image to launch for cloud {0}".format(form['cloud']))
            return False
    ec2run = run_instance(ec2_conn=ec2_conn,
                          user_provided_data=form,
                          image_id=image.image_id,
                          kernel_id=image.kernel_id if image.kernel_id != '' else None,
                          ramdisk_id=image.ramdisk_id if image.ramdisk_id != '' else None,
                          key_name=form["kp_name"],
                          security_groups=[form["sg_name"]],
                          placement=form['placement'])
    if ec2run["rs"] is not None:
        rs = ec2run["rs"]
        request.session['ec2data']['instance_id'] = rs.instances[0].id
        request.session['ec2data']['public_dns'] = rs.instances[0].ip_address #public_dns_name
        request.session['ec2data']['image_id'] = rs.instances[0].image_id
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
    return ec2run["error"]

def userdata(request):
    """Provide file download of user-data to re-start an instance.
    """
    ec2data = request.session["ec2data"]
    response = HttpResponse(mimetype='text/plain')
    response['Content-Disposition'] = 'attachment; filename={cluster_name}-userdata.txt'.format(
        **ec2data)
    ud = _compose_user_data(ec2data)
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
    ec2_conn = connect_ec2(form["access_key"], form["secret_key"], form['cloud'])
    state = instance_state(ec2_conn, form["instance_id"])
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
                        "{0} ({1}){default}".format(iid.image_id, iid.description,
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
                ec2_conn = connect_ec2(a_key, s_key, cloud)
                placements = _find_placements(ec2_conn, inst_type)
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

