from dal import autocomplete
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


class ApplicationVersionCloudConfigForm(ModelForm):

    # def __init__(self, *args, **kwargs):
    #     super(ApplicationVersionCloudConfigForm, self).__init__(*args, **kwargs)
    #     try:
    #         if self.instance and self.instance.target:
    #             self.fields['image'].queryset = models.Image.objects.filter(
    #                 region=self.instance.target.target_zone.region)
    #     except models.ApplicationVersionTargetConfig.target.RelatedObjectDoesNotExist:
    #         pass

    class Meta:
        model = models.ApplicationVersionCloudConfig
        fields = '__all__'
        widgets = {
            'image': autocomplete.ModelSelect2(url='image-autocomplete',
                                               forward=['target'])
        }
