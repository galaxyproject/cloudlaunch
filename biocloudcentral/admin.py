from django.contrib import admin
from biocloudcentral.models import Cloud
from biocloudcentral.models import Image
from biocloudcentral.models import InstanceType
from biocloudcentral.models import DataBucket
from biocloudcentral.models import Usage

class InstanceTypeInline(admin.StackedInline):
    model = InstanceType
    extra = 1
class CloudAdmin(admin.ModelAdmin):
    inlines = [InstanceTypeInline,]
admin.site.register(Cloud, CloudAdmin)

admin.site.register(Image)
admin.site.register(DataBucket)

class UsageAdmin(admin.ModelAdmin):
    model = Usage
    # Enable filtering of displayed entries
    list_filter = ('added', 'cloud_name', 'cloud_type', 'image_id', 'instance_type', 'user_id',)
    # Enable hierarchical navigation by date
    date_hierarchy = 'added'
    # Add search
    search_fields = ['image_id', 'instance_type', 'user_id']

admin.site.register(Usage, UsageAdmin)