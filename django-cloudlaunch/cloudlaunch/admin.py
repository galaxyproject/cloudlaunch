"""Models exposed via Django Admin."""
import ast
from django.contrib import admin
import nested_admin

import djcloudbridge

from polymorphic.admin import PolymorphicChildModelAdmin, PolymorphicParentModelAdmin

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
    ordering = ('display_order',)


class AppCategoryAdmin(admin.ModelAdmin):
    model = models.AppCategory


class CloudImageAdmin(admin.ModelAdmin):
    model = models.Image
    list_display = ('name', 'region', 'image_id')
    list_filter = ('name', 'region')
    ordering = ('name',)


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
class AWSCloudAdmin(PolymorphicChildModelAdmin):
    base_model = models.HostDeploymentTarget


@admin.register(models.KubernetesDeploymentTarget)
class AWSCloudAdmin(PolymorphicChildModelAdmin):
    base_model = models.KubernetesDeploymentTarget


@admin.register(models.DeploymentTarget)
class DeploymentTargetAdmin(PolymorphicParentModelAdmin):
    base_model = models.DeploymentTarget
    child_models = (models.CloudDeploymentTarget, models.HostDeploymentTarget,
                    models.KubernetesDeploymentTarget)


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
