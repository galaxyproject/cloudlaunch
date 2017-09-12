"""Models exposed via Django Admin."""
import ast
from django.contrib import admin
import nested_admin

from baselaunch import forms
from baselaunch import models


class AppVersionCloudConfigInline(nested_admin.NestedTabularInline):
    model = models.ApplicationVersionCloudConfig
    extra = 1


class AppVersionInline(nested_admin.NestedStackedInline):
    model = models.ApplicationVersion
    extra = 0
    inlines = [AppVersionCloudConfigInline]
    form = forms.ApplicationVersionForm


class AppAdmin(nested_admin.NestedModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    inlines = [AppVersionInline]
    form = forms.ApplicationForm


class AppCategoryAdmin(admin.ModelAdmin):
    model = models.AppCategory


class CloudImageInline(admin.StackedInline):
    model = models.CloudImage
    extra = 1


class CloudAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CloudImageInline]


class EC2Admin(admin.ModelAdmin):
    # Hide this model from main app Admin page
    # http://stackoverflow.com/questions/2431727/django-admin-hide-a-model
    get_model_perms = lambda self, req: {}


class S3Admin(admin.ModelAdmin):
    # Hide this model from main app Admin page
    # http://stackoverflow.com/questions/2431727/django-admin-hide-a-model
    get_model_perms = lambda self, req: {}


class AWSCredsInline(admin.StackedInline):
    model = models.AWSCredentials
    form = forms.AWSCredentialsForm
    formset = forms.DefaultRequiredInlineFormSet
    extra = 1


class OSCredsInline(admin.StackedInline):
    model = models.OpenStackCredentials
    form = forms.OpenStackCredentialsForm
    formset = forms.DefaultRequiredInlineFormSet
    extra = 1


class GCECredsInline(admin.StackedInline):
    model = models.GCECredentials
    form = forms.GCECredentialsForm
    formset = forms.DefaultRequiredInlineFormSet
    extra = 1

class AzureCredsInline(admin.StackedInline):
    model = models.AzureCredentials
    form = forms.AzureCredentialsForm
    formset = forms.DefaultRequiredInlineFormSet
    extra = 1


class UserProfileAdmin(admin.ModelAdmin):
    inlines = [AWSCredsInline, OSCredsInline, AzureCredsInline, GCECredsInline]


class AppDeploymentsAdmin(admin.ModelAdmin):
    models = models.ApplicationDeployment


class UsageAdmin(admin.ModelAdmin):
    models = models.Usage
    # Enable column-based display&filtering of entries
    list_display = ('added', 'target_cloud', 'instance_type', 'application',
                    'user')
    # Enable filtering of displayed entries
    list_filter = ('added', 'app_deployment__target_cloud', 'user',
                   'app_deployment__application_version__application__name')
    # Enable hierarchical navigation by date
    date_hierarchy = 'added'
    ordering = ('-added',)
    # Add search
    search_fields = ['user']

    def application(self, obj):
        if obj.app_deployment:
            return obj.app_deployment.application_version.application.name
        return None

    def target_cloud(self, obj):
        if obj.app_deployment:
            return obj.app_deployment.target_cloud.name
        return None
    target_cloud.short_description = 'Target cloud'

    def instance_type(self, obj):
        app_config = ast.literal_eval(obj.app_config)
        return app_config.get('config_cloudlaunch', {}).get('instanceType')


### Public Services ###
class SponsorsAdmin(admin.ModelAdmin):
    models = models.Sponsor


class LocationAdmin(admin.ModelAdmin):
    models = models.Location


class PublicServicesAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    models = models.PublicService


admin.site.register(models.Application, AppAdmin)
admin.site.register(models.AppCategory, AppCategoryAdmin)
admin.site.register(models.ApplicationDeployment, AppDeploymentsAdmin)
admin.site.register(models.AWS, CloudAdmin)
admin.site.register(models.EC2, EC2Admin)
admin.site.register(models.S3, S3Admin)
admin.site.register(models.Azure, CloudAdmin)
admin.site.register(models.OpenStack, CloudAdmin)
admin.site.register(models.GCE, CloudAdmin)
admin.site.register(models.UserProfile, UserProfileAdmin)
admin.site.register(models.Usage, UsageAdmin)

### Public Services Admin Registration ###
admin.site.register(models.PublicService, PublicServicesAdmin)
admin.site.register(models.Sponsor, SponsorsAdmin)
admin.site.register(models.Location, LocationAdmin)
