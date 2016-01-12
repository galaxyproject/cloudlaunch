from django import forms
from django.forms import ModelForm, PasswordInput

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
