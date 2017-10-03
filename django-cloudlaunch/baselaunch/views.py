from django.http import HttpResponse
from django.http.response import FileResponse
from django.http.response import Http404
from rest_framework import filters
from rest_framework import mixins
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
import requests

from baselaunch import drf_helpers
from baselaunch import models
from baselaunch import serializers
from baselaunch import view_helpers


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = models.Application.objects.filter(status=models.Application.LIVE)
    serializer_class = serializers.ApplicationSerializer


class InfrastructureView(APIView):
    """
    List kinds in infrastructures.
    """

    def get(self, request, format=None):
        # We only support cloud infrastructures for the time being
        response = {'url': request.build_absolute_uri('clouds')}
        return Response(response)


class AuthView(APIView):
    """
    List authentication endpoints.
    """

    def get(self, request, format=None):
        data = {'login': request.build_absolute_uri(reverse('rest_auth:rest_login')),
                'logout': request.build_absolute_uri(reverse('rest_auth:rest_logout')),
                'user': request.build_absolute_uri(reverse('rest_auth:rest_user_details')),
                'registration': request.build_absolute_uri(reverse('rest_auth_reg:rest_register')),
                'password/reset': request.build_absolute_uri(reverse('rest_auth:rest_password_reset')),
                'password/reset/confirm': request.build_absolute_uri(reverse('rest_auth:rest_password_reset_confirm')),
                'password/reset/change': request.build_absolute_uri(reverse('rest_auth:rest_password_change')),
                }
        return Response(data)


class CorsProxyView(APIView):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    def get(self, request, format=None):
        url = self.request.query_params.get('url')
        response = requests.get(url)
        return HttpResponse(response.text, status=response.status_code,
                    content_type=response.headers.get('content-type'))


class CloudManViewSet(drf_helpers.CustomReadOnlySingleViewSet):
    """
    List CloudMan related urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.CloudManSerializer


class CloudViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and or edit cloud infrastructure info.
    """
    queryset = models.Cloud.objects.all()
    serializer_class = serializers.CloudSerializer


class ComputeViewSet(drf_helpers.CustomReadOnlySingleViewSet):
    """
    List compute related urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.ComputeSerializer


class RegionViewSet(drf_helpers.CustomReadOnlyModelViewSet):
    """
    List regions in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.RegionSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.compute.regions.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.compute.regions.get(self.kwargs["pk"])
        return obj


class MachineImageViewSet(drf_helpers.CustomModelViewSet):
    """
    List machine images in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.MachineImageSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.compute.images.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.compute.images.get(self.kwargs["pk"])
        return obj


class ZoneViewSet(drf_helpers.CustomReadOnlyModelViewSet):
    """
    List zones in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.ZoneSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        region_pk = self.kwargs.get("region_pk")
        region = provider.compute.regions.get(region_pk)
        if region:
            return region.zones
        else:
            raise Http404

    def get_object(self):
        return next((s for s in self.list_objects()
                     if s.id == self.kwargs["pk"]), None)


class CloudConnectionTestViewSet(mixins.CreateModelMixin,
                                 viewsets.GenericViewSet):
    """
    Authenticates given credentials against a provider
    """
    serializer_class = serializers.CloudConnectionAuthSerializer


class SecurityViewSet(drf_helpers.CustomReadOnlySingleViewSet):
    """
    List security related urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.SecuritySerializer


class KeyPairViewSet(drf_helpers.CustomModelViewSet):
    """
    List key pairs in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.KeyPairSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.security.key_pairs.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.security.key_pairs.get(self.kwargs["pk"])
        return obj


class VMFirewallViewSet(drf_helpers.CustomModelViewSet):
    """
    List VM firewalls in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.VMFirewallSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.security.vm_firewalls.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.security.vm_firewalls.get(self.kwargs["pk"])
        return obj


class VMFirewallRuleViewSet(drf_helpers.CustomModelViewSet):
    """
    List VM firewall rules in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.VMFirewallRuleSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        vmf_pk = self.kwargs.get("vm_firewall_pk")
        vmf = provider.security.vm_firewalls.get(vmf_pk)
        if vmf:
            return vmf.rules.list()
        else:
            raise Http404

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        vmf_pk = self.kwargs.get("vm_firewall_pk")
        vmf = provider.security.vm_firewalls.get(vmf_pk)
        if not vmf:
            raise Http404
        else:
            pk = self.kwargs.get("pk")
            for rule in vmf.rules.list():
                if rule.id == pk:
                    return rule
            raise Http404


class NetworkViewSet(drf_helpers.CustomModelViewSet):
    """
    List networks in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.NetworkSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.networking.networks.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.networking.networks.get(self.kwargs["pk"])
        return obj


class SubnetViewSet(drf_helpers.CustomModelViewSet):
    """
    List networks in a given cloud.
    """
    permission_classes = (IsAuthenticated,)

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.networking.subnets.list(network=self.kwargs["network_pk"])

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.networking.subnets.get(self.kwargs["pk"])

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.SubnetSerializerUpdate
        return serializers.SubnetSerializer


class StaticIPViewSet(drf_helpers.CustomModelViewSet):
    """
    List user's static IP addresses.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.StaticIPSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        ips = []
        for ip in provider.networking.networks.floating_ips:
            if not ip.in_use():
                ips.append({'ip': ip.public_ip})
        return ips


class LargeResultsSetPagination(PageNumberPagination):
    """Modify aspects of the pagination style, primarily page size."""

    page_size = 500
    page_size_query_param = 'page_size'
    max_page_size = 1000


class InstanceTypeViewSet(drf_helpers.CustomReadOnlyModelViewSet):
    """List compute instance types in a given cloud."""
    
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.InstanceTypeSerializer
    pagination_class = LargeResultsSetPagination
    lookup_value_regex = '[^/]+'

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.compute.instance_types.list(limit=500)

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.compute.instance_types.get(self.kwargs.get('pk'))


class InstanceViewSet(drf_helpers.CustomModelViewSet):
    """
    List compute instances in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.InstanceSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.compute.instances.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.compute.instances.get(self.kwargs["pk"])
        return obj

    def perform_destroy(self, instance):
        instance.terminate()


class StorageViewSet(drf_helpers.CustomReadOnlySingleViewSet):
    """
    List storage urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.StorageSerializer


class VolumeViewSet(drf_helpers.CustomModelViewSet):
    """
    List volumes in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.VolumeSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.storage.volumes.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.storage.volumes.get(self.kwargs["pk"])
        return obj


class SnapshotViewSet(drf_helpers.CustomModelViewSet):
    """
    List snapshots in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.SnapshotSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.storage.snapshots.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.storage.snapshots.get(self.kwargs["pk"])
        return obj


class ObjectStoreViewSet(drf_helpers.CustomReadOnlySingleViewSet):
    """
    List compute related urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.StorageSerializer


class BucketViewSet(drf_helpers.CustomModelViewSet):
    """
    List buckets in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.BucketSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.storage.buckets.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.storage.buckets.get(self.kwargs["pk"])
        return obj


class BucketObjectBinaryRenderer(renderers.BaseRenderer):
    media_type = 'application/octet-stream'
    format = 'binary'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        return data


class BucketObjectViewSet(drf_helpers.CustomModelViewSet):
    """
    List objects in a given cloud bucket.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.BucketObjectSerializer
    # Capture everything as a single value
    lookup_value_regex = '.*'
    renderer_classes = drf_helpers.CustomModelViewSet.renderer_classes + \
        [BucketObjectBinaryRenderer]

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        bucket_pk = self.kwargs.get("bucket_pk")
        bucket = provider.storage.buckets.get(bucket_pk)
        if bucket:
            return bucket.objects.list()
        else:
            raise Http404

    def retrieve(self, request, *args, **kwargs):
        bucket_object = self.get_object()
        format = request.query_params.get('format')
        # TODO: This is a bit ugly, since ideally, only the renderer
        # should be aware of the format
        if format == "binary":
            response = FileResponse(streaming_content=bucket_object.iter_content(),
                                    content_type='application/octet-stream')
            response[
                'Content-Disposition'] = 'attachment; filename="%s"' % bucket_object.name
            return response
        else:
            serializer = self.get_serializer(bucket_object)
            return Response(serializer.data)

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        bucket_pk = self.kwargs.get("bucket_pk")
        bucket = provider.storage.buckets.get(bucket_pk)
        if bucket:
            return bucket.objects.get(self.kwargs["pk"])
        else:
            raise Http404


class CredentialsRouteViewSet(drf_helpers.CustomReadOnlySingleViewSet):
    """
    List compute related urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.CredentialsSerializer


class CredentialsViewSet(viewsets.ModelViewSet):

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'userprofile'):
            # Create a user profile if it does not exist
            models.UserProfile.objects.create(user=self.request.user)
        serializer.save(user_profile=self.request.user.userprofile)


class AWSCredentialsViewSet(CredentialsViewSet):
    """
    API endpoint that allows AWS credentials to be viewed or edited.
    """
    queryset = models.AWSCredentials.objects.all()
    serializer_class = serializers.AWSCredsSerializer
    #permission_classes = [permissions.DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'userprofile'):
            return user.userprofile.credentials.filter(
                awscredentials__isnull=False).select_subclasses()
        return models.AWSCredentials.objects.none()


class OpenstackCredentialsViewSet(CredentialsViewSet):
    """
    API endpoint that allows OpenStack credentials to be viewed or edited.
    """
    queryset = models.OpenStackCredentials.objects.all()
    serializer_class = serializers.OpenstackCredsSerializer
    #permission_classes = [permissions.DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'userprofile'):
            return user.userprofile.credentials.filter(
                openstackcredentials__isnull=False).select_subclasses()
        return models.OpenStackCredentials.objects.none()


class AzureCredentialsViewSet(CredentialsViewSet):
    """
    API endpoint that allows Azure credentials to be viewed or edited.
    """
    queryset = models.AzureCredentials.objects.all()
    serializer_class = serializers.AzureCredsSerializer
    #permission_classes = [permissions.DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'userprofile'):
            return user.userprofile.credentials.filter(
                azurecredentials__isnull=False).select_subclasses()
        return models.AzureCredentials.objects.none()


class GCECredentialsViewSet(CredentialsViewSet):
    """
    API endpoint that allows GCE credentials to be viewed or edited.
    """
    queryset = models.GCECredentials.objects.all()
    serializer_class = serializers.GCECredsSerializer
    #permission_classes = [permissions.DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'userprofile'):
            return user.userprofile.credentials.filter(
                gcecredentials__isnull=False).select_subclasses()
        return models.GCECredentials.objects.none()


class DeploymentViewSet(viewsets.ModelViewSet):
    """
    List compute related urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.DeploymentSerializer
    filter_backends = (filters.OrderingFilter,)
    ordering = ('-added',)

    def get_queryset(self):
        """
        This view should return a list of all the deployments
        for the currently authenticated user.
        """
        user = self.request.user
        return models.ApplicationDeployment.objects.filter(owner=user)


class DeploymentTaskViewSet(viewsets.ModelViewSet):
    """List tasks associated with a deployment."""
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.DeploymentTaskSerializer
    filter_backends = (filters.OrderingFilter,)
    ordering = ('-updated',)

    def get_queryset(self):
        """
        This view should return a list of all the tasks
        for the currently associated task.
        """
        deployment = self.kwargs.get('deployment_pk')
        user = self.request.user
        return models.ApplicationDeploymentTask.objects.filter(
            deployment=deployment, deployment__owner=user)


### Public Services ###
class LocationViewSet(viewsets.ModelViewSet):
    """
    List of all locations
    """
    queryset = models.Location.objects.all()
    serializer_class = serializers.LocationSerializer


class SponsorViewSet(viewsets.ModelViewSet):
    """
    List sponsors
    """
    queryset = models.Sponsor.objects.all()
    serializer_class = serializers.SponsorSerializer


class PublicServiceViewSet(viewsets.ModelViewSet):
    """
    List public services
    """
    queryset = models.PublicService.objects.all()
    serializer_class = serializers.PublicServiceSerializer

