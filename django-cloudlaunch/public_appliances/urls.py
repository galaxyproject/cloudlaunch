from django.urls import include
from django.urls import re_path

from . import views

from djcloudbridge.drf_routers import HybridDefaultRouter, HybridNestedRouter, HybridSimpleRouter


router = HybridSimpleRouter()

### Public services ###
router.register(r'services', views.PublicServiceViewSet)
router.register(r'sponsors', views.SponsorViewSet)
router.register(r'locations', views.LocationViewSet)

public_services_regex_pattern = r''

app_name = 'pubapp'

urlpatterns = [
    re_path(public_services_regex_pattern, include(router.urls)),
]
