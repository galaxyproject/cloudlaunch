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
                                           create_key_pair, run_instance)

log = logging.getLogger(__name__)

# Keep user data file template here so no indentation in the file is introduced at print time
UD = """cluster_name: {cluster_name}
password: {password}
freenxpass: {password}
access_key: {access_key}
secret_key: {secret_key}
"""
# ## Landing page with redirects

def home(request):
    launch_url = request.build_absolute_uri("/launch")
    if launch_url.startswith(("http://127.0.0.1", "http://localhost")):
        return redirect("/launch")
    else:
        return redirect("https://biocloudcentral.herokuapp.com/launch")

# ## CloudMan launch and configuration entry details

class CloudManForm(forms.Form):
    """Details needed to boot a setup and boot a CloudMan instance.
    """
    key_url = "https://aws-portal.amazon.com/gp/aws/developer/account/index.html?action=access-key"
    target = "target='_blank'"
    textbox_size = "input_xlarge"
    cluster_name = forms.CharField(required=True,
                                   help_text="Name of your cluster used for identification. "
                                   "This can be any name you choose.",
                                   widget=forms.TextInput(attrs={"class": textbox_size}))
    password = forms.CharField(widget=forms.PasswordInput(render_value=False,
                                                          attrs={"class": "input_xlarge"}),
                               help_text="Your choice of password, for the CloudMan " \
                               "web interface and accessing the Amazon instance via ssh or FreeNX.")
    cloud = forms.ModelChoiceField(queryset=models.Cloud.objects.all(),
                                   help_text="Choose from the available clouds. Note that the credentials "\
                                   "you provide below must match (ie, exist on) the chosen cloud.",
                                   widget=forms.Select(attrs={"class": textbox_size, 
                                     "onChange": "get_instance_types(this.options[this.selectedIndex].value)"}))
    access_key = forms.CharField(required=True,
                                 widget=forms.TextInput(attrs={"class": textbox_size}),
                                 help_text="Your Amazon Access Key ID. Available from "
                                 "the <a href='{0}' {1}>security credentials page</a>.".format(
                                     key_url, target))
    secret_key = forms.CharField(required=True,
                                 widget=forms.TextInput(attrs={"class": textbox_size}),
                                 help_text="Your Amazon Secret Access Key. Also available "
                                 "from the <a href='{0}' {1}>security credentials page</a>.".format(
                                     key_url, target))
    instance_type = forms.ChoiceField((("", "Choose cloud type first"),),
                            help_text="Amazon <a href='{0}' {1}>instance type</a> to start.".format(
                                      "http://aws.amazon.com/ec2/#instance", target),
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
                sg_name = create_cm_security_group(ec2_conn)
                kp_name, kp_material = create_key_pair(ec2_conn)
            except EC2ResponseError, err:
                ec2_error = err.error_message
            # associate form data with session for starting instance
            # and supplying download files
            if ec2_error is None:
                form.cleaned_data["kp_name"] = kp_name
                form.cleaned_data["kp_material"] = kp_material
                form.cleaned_data["sg_name"] = sg_name
                request.session["ec2data"] = form.cleaned_data
                if runinstance(request):
                    return redirect("/monitor")
                else:
                    form.non_field_errors = "A problem starting EC2 instance. " \
                                            "Check AWS console."
            else:
                form.non_field_errors = ec2_error
    else:
        form = CloudManForm()
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
    rs = run_instance(ec2_conn=ec2_conn,
                      user_provided_data=form,
                      key_name=form["kp_name"],
                      security_groups=[form["sg_name"]])
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
    response.write(UD.format(**ec2data))
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
    ec2_conn = connect_ec2(form["access_key"], form["secret_key"])
    info = instance_state(ec2_conn, form["instance_id"])
    state = {'instance_state': info.get("state", ""),
             "public_dns": info.get("dns", "")}
    return HttpResponse(simplejson.dumps(state), mimetype="application/json")

def instancetypes(request):
    if request.is_ajax():
        if request.method == 'POST':
            cloud_id = request.POST.get('cloud_id', '')
            instance_types = []
            if cloud_id != '':
                its = models.InstanceType.objects.filter(cloud=cloud_id)
                for it in its:
                    instance_types.append((it.tech_name, \
                        "{0} ({1})".format(it.pretty_name, it.description)))
            state = {'instance_types': instance_types}
        else:
            log.error("Not a POST request")
    else:
        log.error("No XHR")
    return HttpResponse(simplejson.dumps(state), mimetype="application/json")
    