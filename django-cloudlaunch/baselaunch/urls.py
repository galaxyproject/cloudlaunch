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

from .drf_routers import HybridDefaultRouter, HybridNestedRouter, HybridSimpleRouter


# from django.contrib import admin
# from rest_framework import viewsets
router = HybridDefaultRouter()
router.register(r'applications', views.ApplicationViewSet)
# router.register(r'images', views.ImageViewSet)
router.register(r'infrastructure', views.InfrastructureView,
                base_name='infrastructure')
router.register(r'deployments', views.DeploymentViewSet)
router.register(r'auth', views.AuthView, base_name='auth')

### Public services ###
router.register(r'public_services', views.PublicServiceViewSet)
public_services_router = HybridSimpleRouter()
public_services_router.register(r'sponsors', views.SponsorViewSet)
public_services_router.register(r'locations', views.LocationViewSet)

infra_router = HybridSimpleRouter()
infra_router.register(r'clouds', views.CloudViewSet)

cloud_router = HybridNestedRouter(infra_router, r'clouds', lookup='cloud')

cloud_router.register(r'authenticate', views.CloudConnectionTestViewSet,
                      base_name='compute')
cloud_router.register(r'compute', views.ComputeViewSet,
                      base_name='compute')
cloud_router.register(r'compute/machine_images', views.MachineImageViewSet,
                      base_name='machine_image')
cloud_router.register(r'compute/instance_types', views.InstanceTypeViewSet,
                      base_name='instance_type')
cloud_router.register(r'compute/instances', views.InstanceViewSet,
                      base_name='instance')
cloud_router.register(r'compute/regions', views.RegionViewSet,
                      base_name='region')

cloud_router.register(r'security', views.SecurityViewSet,
                      base_name='security')
cloud_router.register(r'security/keypairs', views.KeyPairViewSet,
                      base_name='keypair')
cloud_router.register(r'security/security_groups', views.SecurityGroupViewSet,
                      base_name='security_group')

cloud_router.register(r'block_store', views.BlockStoreViewSet,
                      base_name='block_store')
cloud_router.register(r'block_store/volumes', views.VolumeViewSet,
                      base_name='volume')
cloud_router.register(r'block_store/snapshots', views.SnapshotViewSet,
                      base_name='snapshot')
cloud_router.register(r'object_store', views.ObjectStoreViewSet,
                      base_name='object_store')
cloud_router.register(r'object_store/buckets', views.BucketViewSet,
                      base_name='bucket')

cloud_router.register(r'networks', views.NetworkViewSet, base_name='network')

cloud_router.register(r'static_ips', views.StaticIPViewSet, base_name='static_ip')


# Deployments should probably go into cloudlaunch, instead of being in baselaunch
# but doing this here for now
cloud_router.register(r'deployments', views.DeploymentViewSet,
                      base_name='deployment')

region_router = HybridNestedRouter(cloud_router, r'compute/regions',
                                   lookup='region')
region_router.register(r'zones', views.ZoneViewSet,
                       base_name='zone')

security_group_router = HybridNestedRouter(cloud_router,
                                           r'security/security_groups',
                                           lookup='security_group')
security_group_router.register(r'rules', views.SecurityGroupRuleViewSet,
                               base_name='security_group_rule')

network_router = HybridNestedRouter(cloud_router, r'networks', lookup='network')
network_router.register(r'subnets', views.SubnetViewSet, base_name='subnet')

bucket_router = HybridNestedRouter(cloud_router, r'object_store/buckets',
                                   lookup='bucket')
bucket_router.register(r'objects', views.BucketObjectViewSet,
                       base_name='bucketobject')

profile_router = HybridSimpleRouter()
profile_router.register(r'credentials', views.CredentialsRouteViewSet,
                        base_name='credentialsroute')
profile_router.register(r'credentials/aws', views.AWSCredentialsViewSet)
profile_router.register(r'credentials/openstack',
                        views.OpenstackCredentialsViewSet)

infrastructure_regex_pattern = r'api/v1/infrastructure/'
auth_regex_pattern = r'api/v1/auth/'
public_services_regex_pattern = r'api/v1/public_services/'
urlpatterns = [
    url(r'api/v1/', include(router.urls)),
    url(infrastructure_regex_pattern, include(infra_router.urls)),
    url(infrastructure_regex_pattern, include(cloud_router.urls)),
    url(infrastructure_regex_pattern, include(region_router.urls)),
    url(infrastructure_regex_pattern, include(security_group_router.urls)),
    url(infrastructure_regex_pattern, include(network_router.urls)),
    url(infrastructure_regex_pattern, include(bucket_router.urls)),
    url(auth_regex_pattern, include('rest_auth.urls', namespace='rest_auth')),
    url(r'api/v1/auth/registration', include('rest_auth.registration.urls',
                                              namespace='rest_auth_reg')),
    url(auth_regex_pattern, include('rest_framework.urls',
                                  namespace='rest_framework')),
    url(r'api/v1/auth/user/', include(profile_router.urls)),
    # The following is required because rest_auth calls allauth internally and
    # reverse urls need to be resolved.
    url(r'accounts/', include('allauth.urls')),
    # Public services
    url(public_services_regex_pattern, include(public_services_router.urls)),
]
