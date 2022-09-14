"""cloudlaunch URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Import the include() function: from django.urls import re_path, include
    3. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf import settings
from django.urls import include
from django.urls import re_path
from rest_framework.schemas import get_schema_view

from . import views

from public_appliances import urls as pub_urls

from djcloudbridge.drf_routers import HybridDefaultRouter, HybridNestedRouter, HybridSimpleRouter
from djcloudbridge.urls import cl_zone_router


# from django.contrib import admin
router = HybridDefaultRouter()
router.register(r'infrastructure', views.InfrastructureView,
                basename='infrastructure')
router.register(r'applications', views.ApplicationViewSet)
# router.register(r'images', views.ImageViewSet)
router.register(r'deployments', views.DeploymentViewSet, basename='deployments')

router.register(r'auth', views.AuthView, basename='auth')
router.register(r'auth/tokens', views.AuthTokenViewSet,
                basename='auth_token')

router.register(r'cors_proxy', views.CorsProxyView, basename='corsproxy')
deployments_router = HybridNestedRouter(router, r'deployments',
                                        lookup='deployment')
deployments_router.register(r'tasks', views.DeploymentTaskViewSet,
                            basename='deployment_task')

# Extend djcloudbridge endpoints
cl_zone_router.register(r'cloudman', views.CloudManViewSet, basename='cloudman')

infrastructure_regex_pattern = r'^api/v1/infrastructure/'
auth_regex_pattern = r'^api/v1/auth/'
public_services_regex_pattern = r'^api/v1/public_services/'

schema_view = get_schema_view(title='CloudLaunch API', url=settings.REST_SCHEMA_BASE_URL,
                              urlconf='cloudlaunch.urls')

registration_urls = [
    re_path(r'^$', views.CustomRegisterView.as_view(), name='rest_register'),
    re_path(r'', include(('dj_rest_auth.registration.urls', 'rest_auth_reg'),
                         namespace='rest_auth_reg'))
]

urlpatterns = [
    re_path(r'^api/v1/', include(router.urls)),
    re_path(r'^api/v1/', include(deployments_router.urls)),
    # This generates a duplicate url set with the cloudman url included
    # get_urls() must be called or a cached set of urls will be returned.
    re_path(infrastructure_regex_pattern, include(cl_zone_router.get_urls())),
    re_path(infrastructure_regex_pattern, include('djcloudbridge.urls')),
    re_path(auth_regex_pattern, include(('dj_rest_auth.urls', 'rest_auth'), namespace='rest_auth')),

    # Override default register view
    re_path(r'%sregistration' % auth_regex_pattern, include((registration_urls, 'rest_auth_reg'), namespace='rest_auth_reg')),
    re_path(r'%suser/public-keys/$' %
        auth_regex_pattern, views.PublicKeyList.as_view()),
    re_path(r'%suser/public-keys/(?P<pk>[0-9]+)/$' %
            auth_regex_pattern, views.PublicKeyDetail.as_view(),
            name='public-key-detail'),
    re_path(auth_regex_pattern, include(('rest_framework.urls', 'rest_framework'),
                                        namespace='rest_framework')),
    re_path(auth_regex_pattern, include('djcloudbridge.profile.urls')),
    # The following is required because rest_auth calls allauth internally and
    # reverse urls need to be resolved.
    re_path(r'^accounts/', include('allauth.urls')),
    # Public services
    re_path(public_services_regex_pattern, include('public_appliances.urls')),
    re_path(r'^api/v1/schema/$', schema_view),
    re_path(r'^image-autocomplete/$', views.ImageAutocomplete.as_view(),
            name='image-autocomplete',
    )
]
