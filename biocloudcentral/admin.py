from django.contrib import admin
from biocloudcentral.models import Cloud
from biocloudcentral.models import Image
from biocloudcentral.models import InstanceType

class InstanceTypeInline(admin.StackedInline):
    model = InstanceType
    extra = 1
class CloudAdmin(admin.ModelAdmin):
    inlines = [InstanceTypeInline,]
admin.site.register(Cloud, CloudAdmin)

admin.site.register(Image)