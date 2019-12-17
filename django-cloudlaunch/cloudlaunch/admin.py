"""Models exposed via Django Admin."""
import ast
from django.http import HttpResponse
from django.core.management import call_command
from django.conf import settings
from django.contrib import admin
from django.shortcuts import render
from django.contrib import messages
from django.utils.translation import gettext as _
import nested_admin

import djcloudbridge

from polymorphic.admin import PolymorphicChildModelAdmin
from polymorphic.admin import PolymorphicParentModelAdmin
from polymorphic.admin import PolymorphicChildModelFilter

from . import forms
from . import models


class AppVersionCloudConfigInline(nested_admin.NestedTabularInline):
    model = models.ApplicationVersionCloudConfig
    extra = 1
    form = forms.ApplicationVersionCloudConfigForm


class AppVersionInline(nested_admin.NestedStackedInline):
    model = models.ApplicationVersion
    extra = 0
    inlines = [AppVersionCloudConfigInline]
    form = forms.ApplicationVersionForm


class AppAdmin(nested_admin.NestedModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    inlines = [AppVersionInline]
    form = forms.ApplicationForm
    list_display = ('name', 'default_version')
    ordering = ('display_order',)


class AppCategoryAdmin(admin.ModelAdmin):
    model = models.AppCategory


class CloudImageAdmin(admin.ModelAdmin):
    model = models.Image
    list_display = ('name', 'region', 'image_id')
    list_filter = ('region__cloud', 'region', 'name')
    ordering = ('region',)


# Utility class for read-only fields
class ReadOnlyTabularInline(admin.TabularInline):
    extra = 0
    can_delete = False
    editable_fields = []
    readonly_fields = []
    exclude = []

    def get_readonly_fields(self, request, obj=None):
        return list(self.readonly_fields) + \
               [field.name for field in self.model._meta.fields
                if field.name not in self.editable_fields and
                   field.name not in self.exclude]


class AppDeployTaskAdmin(ReadOnlyTabularInline):
    model = models.ApplicationDeploymentTask
    ordering = ('added',)


class AppDeploymentsAdmin(admin.ModelAdmin):
    models = models.ApplicationDeployment
    list_display = ('name', 'archived', 'owner')
    list_filter = ('archived', 'owner__username')
    inlines = [AppDeployTaskAdmin]


@admin.register(models.CloudDeploymentTarget)
class AWSCloudAdmin(PolymorphicChildModelAdmin):
    base_model = models.CloudDeploymentTarget


@admin.register(models.HostDeploymentTarget)
class HostCloudAdmin(PolymorphicChildModelAdmin):
    base_model = models.HostDeploymentTarget


@admin.register(models.KubernetesDeploymentTarget)
class K8sCloudAdmin(PolymorphicChildModelAdmin):
    base_model = models.KubernetesDeploymentTarget


@admin.register(models.DeploymentTarget)
class DeploymentTargetAdmin(PolymorphicParentModelAdmin):
    base_model = models.DeploymentTarget
    child_models = (models.CloudDeploymentTarget, models.HostDeploymentTarget,
                    models.KubernetesDeploymentTarget)
    list_display = ('id', 'custom_column')
    list_filter = (PolymorphicChildModelFilter,)

    def custom_column(self, obj):
        return models.DeploymentTarget.objects.get(pk=obj.id).__str__()
    custom_column.short_description = ("Deployment Target")


class UsageAdmin(admin.ModelAdmin):
    models = models.Usage

    def deployment_target(self, obj):
        if obj.app_deployment:
            return obj.app_deployment.deployment_target
        return None
    deployment_target.short_description = 'Deployment Target'

    def application(self, obj):
        if obj.app_deployment:
            return obj.app_deployment.application_version.application.name
        return None

    def instance_type(self, obj):
        app_config = ast.literal_eval(obj.app_config)
        return app_config.get('config_cloudlaunch', {}).get('instanceType')

    # Enable column-based display&filtering of entries
    list_display = ('added', 'deployment_target', 'instance_type', 'application',
                    'user')
    # Enable filtering of displayed entries
    list_filter = ('added', 'app_deployment__deployment_target', 'user',
                   'app_deployment__application_version__application__name')
    # Enable hierarchical navigation by date
    date_hierarchy = 'added'
    ordering = ('-added',)
    # Add search
    search_fields = ['user']


class PublicKeyInline(admin.StackedInline):
    model = models.PublicKey
    extra = 1


class UserProfileAdmin(djcloudbridge.admin.UserProfileAdmin):
    inlines = djcloudbridge.admin.UserProfileAdmin.inlines + [PublicKeyInline]


admin.site.register(models.Application, AppAdmin)
admin.site.register(models.AppCategory, AppCategoryAdmin)
admin.site.register(models.ApplicationDeployment, AppDeploymentsAdmin)
admin.site.register(models.Image, CloudImageAdmin)
admin.site.register(models.Usage, UsageAdmin)

# Add public key to existing UserProfile
admin.site.unregister(djcloudbridge.models.UserProfile)
admin.site.register(djcloudbridge.models.UserProfile, UserProfileAdmin)


# Django Site Admin import/export actions

def import_app_data(modeladmin, request, queryset):
    # All requests here will actually be of type POST
    # so we will need to check for our special key 'apply'
    # rather than the actual request type
    if request.POST.get('post'):
        # The user clicked submit on the intermediate form.
        # Perform our update action:
        app_registry_url = request.POST['app_registry_url']
        call_command('import_app_data', '-u', app_registry_url)

        modeladmin.message_user(
            request,
            _("Successfully imported registry from url: %(app_registry_url)s") % {
                "app_registry_url": app_registry_url}, messages.SUCCESS)
        return None

    return render(request, 'admin/import_data.html',
                  context={'app_registry_url': settings.CLOUDLAUNCH_APP_REGISTRY_URL,
                           'rows': queryset})


import_app_data.short_description = "Import app data from url"


def export_app_data(modeladmin, request, queryset):
    response = HttpResponse(content_type="application/yaml")
    response['Content-Disposition'] = 'attachment; filename="app-registry.yaml"'
    response.write(call_command('export_app_data'))
    return response


export_app_data.short_description = "Export app data to file"

admin.site.add_action(import_app_data)
admin.site.add_action(export_app_data)