from django.forms import ModelForm

from . import models
from djcloudbridge import models as cb_models


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
            self.fields['default_target'].queryset = models.DeploymentTarget.objects.filter(app_version_config__application_version=self.instance)
            
    class Meta:
        model = models.ApplicationVersion
        fields = '__all__'
