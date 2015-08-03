from django.contrib import admin
from biocloudcentral import settings
from biocloudcentral.models import Cloud
from biocloudcentral.models import Image
from biocloudcentral.models import Flavor
from biocloudcentral.models import InstanceType
from biocloudcentral.models import DataBucket
from biocloudcentral.models import Usage
from biocloudcentral.forms import FlavorAdminForm


class InstanceTypeInline(admin.StackedInline):
    model = InstanceType
    extra = 1


class CloudAdmin(admin.ModelAdmin):
    inlines = [InstanceTypeInline]
admin.site.register(Cloud, CloudAdmin)


class FlavorInline(admin.StackedInline):
    model = Flavor
    form = FlavorAdminForm
    extra = 1


class ImageAdmin(admin.ModelAdmin):
    inlines = [FlavorInline]

admin.site.register(Image, ImageAdmin)
admin.site.register(DataBucket)


class UsageAdmin(admin.ModelAdmin):
    model = Usage
    # Enable column-based display&filtering of entries
    list_display = ('added', 'cloud_name', 'image_id', 'instance_type',
                    'cluster_type', 'storage_type', 'storage_size', 'user_id')
    # Enable filtering of displayed entries
    list_filter = ('added', 'cloud_name', 'instance_type',
                   'cluster_type', 'storage_type', 'image_id', 'user_id')
    if hasattr(settings, 'ASK_FOR_EMAIL') and settings.ASK_FOR_EMAIL:
        list_display += ('email',)
        list_filter += ('email',)
    # Enable hierarchical navigation by date
    date_hierarchy = 'added'
    ordering = ('-added',)
    # Add search
    search_fields = ['image_id', 'instance_type', 'user_id']

admin.site.register(Usage, UsageAdmin)


class FlavorAdmin(admin.ModelAdmin):
    form = FlavorAdminForm

# admin.site.register(Flavor, FlavorAdmin)
