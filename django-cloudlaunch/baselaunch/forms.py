from django import forms
from django.forms import ModelForm
from django.forms import PasswordInput
from django.forms.models import BaseInlineFormSet

from baselaunch import models


class AWSCredentialsForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(AWSCredentialsForm, self).__init__(*args, **kwargs)
        # restrict choices to AWS clouds only
        self.fields['cloud'].queryset = models.AWS.objects.all()

    secret_key = forms.CharField(widget=PasswordInput(render_value=True),
                                 required=False)

    class Meta:
        model = models.AWSCredentials
        fields = '__all__'


class OpenStackCredentialsForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(OpenStackCredentialsForm, self).__init__(*args, **kwargs)
        # restrict choices to Openstack clouds only
        self.fields['cloud'].queryset = models.OpenStack \
            .objects.all()

    password = forms.CharField(widget=PasswordInput(render_value=True),
                               required=False)

    class Meta:
        model = models.OpenStackCredentials
        fields = '__all__'

class GCECredentialsForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(GCECredentialsForm, self).__init__(*args, **kwargs)
        # restrict choices to GCE clouds only
        self.fields['cloud'].queryset = models.GCE.objects.all()

    class Meta:
        model = models.GCECredentials
        fields = '__all__'

class AzureCredentialsForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(AzureCredentialsForm, self).__init__(*args, **kwargs)
        # restrict choices to Azure clouds only
        self.fields['cloud'].queryset = models.Azure \
            .objects.all()

    secret = forms.CharField(widget=PasswordInput(render_value=True),
                               required=False)

    class Meta:
        model = models.AzureCredentials
        fields = '__all__'


class DefaultRequiredInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super(DefaultRequiredInlineFormSet, self).clean()
        if any(self.errors):
            return


class ApplicationForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(ApplicationForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['default_version'].queryset = models.ApplicationVersion.objects.filter(application=self.instance)
            
    class Meta:
        model = models.Application
        fields = '__all__'


class ApplicationVersionForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(ApplicationVersionForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['default_cloud'].queryset = models.Cloud.objects.filter(app_version_config__application_version=self.instance)
            
    class Meta:
        model = models.ApplicationVersion
        fields = '__all__'
