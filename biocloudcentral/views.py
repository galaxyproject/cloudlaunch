"""Base views.
"""
import logging

from django.http import HttpResponse
from django.template import RequestContext
from django import forms
from django.utils import simplejson
from django.shortcuts import render, redirect

from boto.exception import EC2ResponseError

from biocloudcentral import models
from biocloudcentral.amazon.launch import (connect_ec2, instance_state,
                                           create_cm_security_group,
                                           create_key_pair, run_instance,
                                           _compose_user_data, _find_placement)

log = logging.getLogger(__name__)

# ## Landing page with redirects

def home(request):
    launch_url = request.build_absolute_uri("/launch")
    if launch_url.startswith(("http://127.0.0.1", "http://localhost")):
        return redirect("/launch")
    else:
        return redirect("https://biocloudcentral.herokuapp.com/launch")

# ## CloudMan launch and configuration entry details

class DynamicChoiceField(forms.ChoiceField):
    """ Override the ChoiceField to allow AJAX-populated choices in the 
        part of the form.
    """
    def valid_value(self, value):
        # TODO: Add some validation code to ensure passed data is valid.
        # Return True if value is valid else return False
        return True
    

class CloudManForm(forms.Form):
    """Details needed to boot a setup and boot a CloudMan instance.
    """
    key_url = "https://aws-portal.amazon.com/gp/aws/developer/account/index.html?action=access-key"
    ud_url = "http://wiki.g2.bx.psu.edu/Admin/Cloud/UserData"
    target = "target='_blank'"
    textbox_size = "input_xlarge"
    cluster_name = forms.CharField(required=True,
                                   help_text="Name of your cluster used for identification. "
                                   "This can be any name you choose.",
                                   widget=forms.TextInput(attrs={"class": textbox_size}))
    password = forms.CharField(widget=forms.PasswordInput(render_value=False,
                                                          attrs={"class": "input_xlarge"}),
                               help_text="Your choice of password, for the CloudMan " \
                               "web interface and accessing the instance via ssh or FreeNX.")
    cloud = forms.ModelChoiceField(queryset=models.Cloud.objects.all(),
                                   help_text="Choose from the available clouds. The credentials "\
                                   "you provide below must match (ie, exist on) the chosen cloud.",
                                   widget=forms.Select(attrs={"class": textbox_size, 
                                   "onChange": "get_dynamic_fields(this.options[this.selectedIndex].value)"}))
    access_key = forms.CharField(required=True,
                                 widget=forms.TextInput(attrs={"class": textbox_size}),
                                 help_text="Your Access Key ID. For the Amazon cloud, available from "
                                 "the <a href='{0}' {1} tabindex='-1'>security credentials page</a>.".format(
                                     key_url, target))
    secret_key = forms.CharField(required=True,
                                 widget=forms.TextInput(attrs={"class": textbox_size}),
                                 help_text="Your Secret Access Key. For the Amazon cloud, also available "
                                 "from the <a href='{0}' {1} tabindex='-1'>security credentials page</a>."\
                                 .format(key_url, target))
    instance_type = DynamicChoiceField((("", "Choose cloud type first"),),
                            help_text="Type (ie, virtual hardware configuration) of the instance to start.",
                            widget=forms.Select(attrs={"class": textbox_size, 'disabled': 'disabled'}))
    placement = DynamicChoiceField((("", "Fill above fields & click refresh to fetch"),),
                            help_text="A specific placement zone where your instance will run. This "
                            "requires you have filled out the previous 4 fields!",
                            required=False,
                            widget=forms.Select(attrs={"class": textbox_size, 'disabled': 'disabled'}))
    post_start_script_url = forms.CharField(required=False,
                              label="Post-start script",
                              widget=forms.TextInput(attrs={"class": textbox_size}),
                              help_text="A URL to the post-start script. See <a href='{0}' {1} tabindex='-1'>"
                              "CloudMan's wiki</a> for a detailed description of this option."\
                              .format(ud_url, target))
    worker_post_start_script_url = forms.CharField(required=False,
                              label="Worker post-start script",
                              widget=forms.TextInput(attrs={"class": textbox_size}),
                              help_text="A URL to the post-start script for worker nodes. See "
                              "<a href='{0}' {1} tabindex='-1'>CloudMan's wiki</a> for the description."\
                              .format(ud_url, target))
    image_id = DynamicChoiceField((("", "Choose cloud type first"),),
                            help_text="The machine image to start (* indicates the default machine image).",
                            label="Image ID",
                            required=False,
                            widget=forms.Select(attrs={"class": textbox_size, 'disabled': 'disabled'}))
    
def launch(request):
    """Configure and launch CloudBioLinux and CloudMan servers.
    """
    if request.method == "POST":
        form = CloudManForm(request.POST)
        if form.is_valid():
            print form.cleaned_data
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
                if runinstance(request):
                    return redirect("/monitor")
                else:
                    form.non_field_errors = "A problem starting your instance. " \
                                            "Check the {0} cloud's console."\
                                            .format(form.cleaned_data['cloud'].name)
            else:
                form.non_field_errors = ec2_error
    else:
        # Select the first item in the clouds dropdown, thus potentially eliminating
        # that click for the most commonly used cloud. This does assume the most used
        # cloud is the first in the DB and that such an entry exists in the first place
        form = CloudManForm(initial={'cloud': 1})
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
    rs = run_instance(ec2_conn=ec2_conn,
                      user_provided_data=form,
                      image_id=image.image_id,
                      kernel_id=image.kernel_id if image.kernel_id != '' else None,
                      ramdisk_id=image.ramdisk_id if image.ramdisk_id != '' else None,
                      key_name=form["kp_name"],
                      security_groups=[form["sg_name"]],
                      placement=form['placement'])
    if rs is not None:
        request.session['ec2data']['instance_id'] = rs.instances[0].id
        request.session['ec2data']['public_dns'] = rs.instances[0].public_dns_name
        request.session['ec2data']['image_id'] = rs.instances[0].image_id
        return True
    else:
        return False

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

def get_placements(request):
    if request.is_ajax():
        if request.method == 'POST':
            cloud_id = request.POST.get('cloud_id', '')
            a_key = request.POST.get('a_key', '')
            s_key = request.POST.get('s_key', '')
            inst_type = request.POST.get('instance_type', '')
            placements = []
            if cloud_id != '' and a_key != '' and s_key != '' and inst_type != '':
                # Needed to get the cloud connection
                cloud = models.Cloud.objects.get(pk=cloud_id)
                ec2_conn = connect_ec2(a_key, s_key, cloud)
                placements = _find_placement(ec2_conn, inst_type, cloud.cloud_type, get_all=True)
                state = {'placements': placements}
        else:
            log.error("Not a POST request")
    else:
        log.error("No XHR")
    return HttpResponse(simplejson.dumps(state), mimetype="application/json")
