"""Base views.
"""
from django.http import HttpResponse
from django import forms
from django.shortcuts import render, redirect

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
    cluster_name = forms.CharField(required=True,
                                   help_text="Name of your cluster used for identification. "
                                   "This can be any name you choose.")
    password = forms.CharField(widget=forms.PasswordInput(render_value=False),
                               help_text="Password used to access the CloudMan web interface "
                               "and your instance via ssh and FreeNX.")
    access_key = forms.CharField(required=True,
                                 help_text="Your Amazon Access Key ID. Available from "
                                 "the security credentials page.")
    secret_key = forms.CharField(required=True,
                                 help_text="Your Amazon Secret Access Key. Also available "
                                 "from the security credentials page.")
    instance_type = forms.ChoiceField((("m1.large", "Large"),
                                       ("t1.micro", "Micro"),
                                       ("m1.xlarge", "Extra Large")),
                                      help_text="Amazon instance type to start.")

def launch(request):
    """Configure and launch CloudBioLinux and CloudMan servers.
    """
    if request.method == "POST":
        form = CloudManForm(request.POST)
        if form.is_valid():
            print form.cleaned_data
            return HttpResponse("Sweet")
    else:
        form = CloudManForm()
    return render(request, "launch.html", {"form": form})
