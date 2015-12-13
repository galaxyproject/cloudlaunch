from django.contrib import admin

from .models import Application
from .models import AWSEC2
from .models import AWSS3
from .models import Category
from .models import Image
from .models import OpenStack


class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}

admin.site.register(Application)
admin.site.register(Category, CategoryAdmin)
admin.site.register(AWSEC2)
admin.site.register(AWSS3)
admin.site.register(OpenStack)
admin.site.register(Image)
