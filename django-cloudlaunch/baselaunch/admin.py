from django.contrib import admin

from .models import Application
from .models import ApplicationVersion
from .models import AWSEC2
from .models import AWSS3
from .models import Image
from .models import OpenStack


class AppVersionInline(admin.StackedInline):
    model = ApplicationVersion
    extra = 1


class AppAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    inlines = [AppVersionInline]

admin.site.register(Application, AppAdmin)
admin.site.register(AWSEC2)
admin.site.register(AWSS3)
admin.site.register(OpenStack)
admin.site.register(Image)
