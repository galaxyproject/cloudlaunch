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
    2. Import the include() function: from django.conf.urls import url, include
    3. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include
from django.conf.urls import url

from . import views

from public_appliances import urls as pub_urls

from djcloudbridge.drf_routers import HybridDefaultRouter, HybridNestedRouter, HybridSimpleRouter
from djcloudbridge.urls import cloud_router


# from django.contrib import admin
router = HybridDefaultRouter()
router.register(r'infrastructure', views.InfrastructureView,
                base_name='infrastructure')
router.register(r'applications', views.ApplicationViewSet)
# router.register(r'images', views.ImageViewSet)
router.register(r'deployments', views.DeploymentViewSet, base_name='deployments')
router.register(r'auth', views.AuthView, base_name='auth')
router.register(r'cors_proxy', views.CorsProxyView, base_name='corsproxy')
deployments_router = HybridNestedRouter(router, r'deployments',
                                        lookup='deployment')
deployments_router.register(r'tasks', views.DeploymentTaskViewSet,
                            base_name='deployment_task')

# Extend djcloudbridge endpoints
cloud_router.register(r'cloudman', views.CloudManViewSet, base_name='cloudman')

infrastructure_regex_pattern = r'api/v1/infrastructure/'
auth_regex_pattern = r'api/v1/auth/'
public_services_regex_pattern = r'api/v1/public_services/'
urlpatterns = [
    url(r'api/v1/', include(router.urls)),
    url(r'api/v1/', include(deployments_router.urls)),
    # This generates a duplicate url set with the cloudman url included
    # get_urls() must be called or a cached set of urls will be returned.
    url(infrastructure_regex_pattern, include(cloud_router.get_urls())),
    url(infrastructure_regex_pattern, include('djcloudbridge.urls')),
    url(auth_regex_pattern, include('rest_auth.urls', namespace='rest_auth')),
    url(r'api/v1/auth/registration', include('rest_auth.registration.urls',
                                              namespace='rest_auth_reg')),
    url(auth_regex_pattern, include('rest_framework.urls',
                                  namespace='rest_framework')),
    url(r'api/v1/auth/', include('djcloudbridge.profile.urls')),
    # The following is required because rest_auth calls allauth internally and
    # reverse urls need to be resolved.
    url(r'accounts/', include('allauth.urls')),
    # Public services
    url(public_services_regex_pattern, include('public_appliances.urls')),
]
