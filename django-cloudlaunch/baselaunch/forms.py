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


class DefaultRequiredInlineFormSet(BaseInlineFormSet):

    def clean(self):
        """Check that at least one default credentials has been set."""
        super(DefaultRequiredInlineFormSet, self).clean()
        if any(self.errors):
            return
        if not any(cleaned_data.get('default') for cleaned_data in self.cleaned_data):
            raise forms.ValidationError('At least one default credentials are required.')
