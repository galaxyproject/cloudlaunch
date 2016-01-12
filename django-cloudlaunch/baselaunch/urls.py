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

from baselaunch import views

from .util import HybridDefaultRouter, HybridNestedRouter, HybridSimpleRouter


# from django.contrib import admin
# from rest_framework import viewsets
router = HybridDefaultRouter()
router.register(r'applications', views.ApplicationViewSet)
# router.register(r'images', views.ImageViewSet)
router.register(r'infrastructure', views.InfrastructureView,
                base_name='infrastructure')
router.register(r'auth', views.AuthView, base_name='auth')

infra_router = HybridSimpleRouter()
infra_router.register(r'clouds', views.CloudViewSet)

cloud_router = HybridNestedRouter(infra_router, r'clouds', lookup='cloud')
cloud_router.register(r'regions', views.RegionViewSet, base_name='region')
cloud_router.register(r'keypairs', views.KeyPairViewSet, base_name='keypair')
cloud_router.register(r'security_groups', views.SecurityGroupViewSet,
                      base_name='security_group')
cloud_router.register(r'block_store/volumes', views.VolumeViewSet,
                      base_name='volume')
cloud_router.register(r'block_store/snapshots', views.SnapshotViewSet,
                      base_name='snapshot')
cloud_router.register(r'object_store/buckets', views.BucketViewSet,
                      base_name='bucket')

bucket_router = HybridNestedRouter(cloud_router, r'object_store/buckets',
                                   lookup='bucket')
bucket_router.register(r'objects', views.BucketObjectViewSet,
                       base_name='object')

urlpatterns = [
    url(r'^api/v1/', include(router.urls)),
    url(r'^api/v1/infrastructure/', include(infra_router.urls)),
    url(r'^api/v1/infrastructure/', include(cloud_router.urls)),
    url(r'^api/v1/infrastructure/', include(bucket_router.urls)),
    url(r'^api/v1/auth/', include('rest_auth.urls', namespace='rest_auth')),
    url(r'^api/v1/auth/registration', include('rest_auth.registration.urls',
                                              namespace='rest_auth_reg')),
    url(r'^api/v1/auth/', include('rest_framework.urls',
                                  namespace='rest_framework')),
    # The following is required because rest_auth calls allauth internally and
    # reverse urls need to be resolved.
    url(r'^accounts/', include('allauth.urls')),
]
