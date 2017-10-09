from django.contrib import admin

from . import models

### Public Services ###
class SponsorsAdmin(admin.ModelAdmin):
    models = models.Sponsor


class LocationAdmin(admin.ModelAdmin):
    models = models.Location


class PublicServicesAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    models = models.PublicService


### Public Services Admin Registration ###
admin.site.register(models.PublicService, PublicServicesAdmin)
admin.site.register(models.Sponsor, SponsorsAdmin)
admin.site.register(models.Location, LocationAdmin)

