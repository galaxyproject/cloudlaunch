"""Base views.
"""
from django.http import HttpResponse
from django import forms
from django.shortcuts import render, redirect

from biocloudcentral.amazon.launch import (connect_ec2, create_iam_user,
                                           create_cm_security_group,
                                           create_key_pair, run_instance)

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
    cluster_name = forms.CharField(required=True,
                                   help_text="Name of your cluster used for identification. "
                                   "This can be any name you choose.")
    password = forms.CharField(widget=forms.PasswordInput(render_value=False),
                               help_text="Your choice of password, for the CloudMan " \
                               "web interface and accessing the Amazon instance via ssh or FreeNX.")
    access_key = forms.CharField(required=True,
                                 help_text="Your Amazon Access Key ID. Available from "
                                 "the <a href='{0}' {1}>security credentials page</a>.".format(
                                     key_url, target))
    secret_key = forms.CharField(required=True,
                                 help_text="Your Amazon Secret Access Key. Also available "
                                 "from the <a href='{0}' {1}>security credentials page</a>.".format(
                                     key_url, target))
    instance_type = forms.ChoiceField((("m1.large", "Large"),
                                       ("t1.micro", "Micro"),
                                       ("m1.xlarge", "Extra Large")),
                            help_text="Amazon <a href='{0}' {1}>instance type</a> to start.".format(
                                      "http://aws.amazon.com/ec2/#instance", target))

def launch(request):
    """Configure and launch CloudBioLinux and CloudMan servers.
    """
    if request.method == "POST":
        form = CloudManForm(request.POST)
        if form.is_valid():
            print form.cleaned_data
            rs = None
            # Create security group & key pair with original creds and then
            # create IAM identity that will run the cluster but have reduced
            # set of privileges
            ec2_conn = connect_ec2(form.cleaned_data['access_key'], form.cleaned_data['secret_key'])
            sg_name = create_cm_security_group(ec2_conn)
            kp_name = create_key_pair(ec2_conn)
            a_key, s_key = create_iam_user(form.cleaned_data['access_key'], form.cleaned_data['secret_key'])
            # Recreate EC2 connection with newly created creds
            ec2_conn = connect_ec2(a_key, s_key)
            rs = run_instance(ec2_conn=ec2_conn, \
                              user_provided_data=form.cleaned_data, \
                              key_name=kp_name, \
                              security_groups=[sg_name])
            if rs is not None:
                return HttpResponse('Started an instance with ID %s and IP <a href="http://%s/cloud" target="_blank">%s</a>' \
                    % (rs.instances[0].id, rs.instances[0].public_dns_name, rs.instances[0].public_dns_name))
            else:
                return HttpResponse('A problem starting an instance. Check AWS console.')
    else:
        form = CloudManForm()
    return render(request, "launch.html", {"form": form})
