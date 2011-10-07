"""Base views.
"""
from django.http import HttpResponse
from django import forms
from django.shortcuts import render

class CloudManForm(forms.Form):
    """Details needed to boot a setup and boot a CloudMan instance.
    """
    cluster_name = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput(render_value=False))
    access_key = forms.CharField(required=True)
    secret_key = forms.CharField(required=True)

def home(request):
    if request.method == "POST":
        form = CloudManForm(request.POST)
        if form.is_valid():
            return HttpResponse("Sweet")
    else:
        form = CloudManForm()
    return render(request, "home.html", {"form": form})
