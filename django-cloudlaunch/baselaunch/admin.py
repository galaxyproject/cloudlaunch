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


admin.site.register(models.Application, AppAdmin)
admin.site.register(models.AppCategory, AppCategoryAdmin)
admin.site.register(models.ApplicationDeployment, AppDeploymentsAdmin)
admin.site.register(models.Usage, UsageAdmin)
