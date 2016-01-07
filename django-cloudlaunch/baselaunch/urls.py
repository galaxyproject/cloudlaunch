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
# from django.contrib import admin
from rest_auth import views as rest_auth_views
from rest_auth.registration import views as rest_reg_views
# from rest_framework import viewsets
from baselaunch import views
from .util import HybridRouter


router = HybridRouter()
router.register(r'applications', views.ApplicationViewSet)
# router.register(r'images', views.ImageViewSet)
router.register(r'infrastructure/clouds', views.CloudViewSet)
router.register(r'infrastructure', views.InfrastructureView,
                base_name='infrastructure')
# django rest-auth
router.register(r'auth', views.AuthView,
                base_name='auth')

urlpatterns = [
    url(r'^api/v1/', include(router.urls)),
    url(r'^api/v1/auth/', include('rest_auth.urls', namespace='rest_auth')),
    url(r'^api/v1/auth/registration', include('rest_auth.registration.urls',
                                              namespace='rest_auth_reg')),
    url(r'^api/v1/auth/', include('rest_framework.urls',
                                  namespace='rest_framework')),
]
