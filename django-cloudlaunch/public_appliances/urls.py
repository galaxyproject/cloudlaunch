from django.conf.urls import include
from django.conf.urls import url

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
    url(public_services_regex_pattern, include(router.urls)),
]
