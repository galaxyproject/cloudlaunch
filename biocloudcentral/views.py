"""Base views.
"""
from django.http import HttpResponse
from django import forms
from django.shortcuts import render, redirect

def home(request):
    launch_url = request.build_absolute_uri("/launch")
    if launch_url.startswith(("http://127.0.0.1", "http://localhost")):
        return redirect("/launch")
    else:
        return redirect("https://biocloudcentral.herokuapp.com/launch")

# -- cloudman configuration entry details

class CloudManForm(forms.Form):
    """Details needed to boot a setup and boot a CloudMan instance.
    """
    cluster_name = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput(render_value=False))
    access_key = forms.CharField(required=True)
    secret_key = forms.CharField(required=True)

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
