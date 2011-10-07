"""Base views.
"""
from django.http import HttpResponse
from django import forms
from django.shortcuts import render_to_response

class CloudManForm(forms.Form):
    """Details needed to boot a setup and boot a CloudMan instance.
    """
    cluster_name = forms.CharField(required=True)
    password = forms.CharField(label=_(u'Password'),
                               widget=forms.PasswordInput(render_value=False))
    access_key = forms.CharField(required=True)
    secret_key = forms.CharField(required=True)

def home(request):
    if require.method == "POST":
        form = CloudManForm(require.POST)
        if form.is_valid():
            return HttpResponse("Sweet")
    else:
        form = CloudManForm()
    return render_to_response("home.html", {"form": form})
