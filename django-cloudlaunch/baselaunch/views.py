from django.http.response import FileResponse
from django.http.response import Http404
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from baselaunch import drf_helpers
from baselaunch import models
from baselaunch import serializers
from baselaunch import view_helpers


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = models.Application.objects.all()
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


class SecurityGroupViewSet(drf_helpers.CustomModelViewSet):
    """
    List security groups in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.SecurityGroupSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.security.security_groups.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.security.security_groups.get(self.kwargs["pk"])
        return obj


class SecurityGroupRuleViewSet(drf_helpers.CustomModelViewSet):
    """
    List security group rules in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.SecurityGroupRuleSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        sg_pk = self.kwargs.get("security_group_pk")
        sg = provider.security.security_groups.get(sg_pk)
        if sg:
            return sg.rules
        else:
            raise Http404

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        sg_pk = self.kwargs.get("security_group_pk")
        sg = provider.security.security_groups.get(sg_pk)
        if not sg:
            raise Http404
        else:
            pk = self.kwargs.get("pk")
            for rule in sg.rules:
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
        return provider.network.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.network.get(self.kwargs["pk"])
        return obj


class SubnetViewSet(drf_helpers.CustomModelViewSet):
    """
    List networks in a given cloud.
    """
    permission_classes = (IsAuthenticated,)

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.network.subnets.list(network=self.kwargs["network_pk"])

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.network.subnets.get(self.kwargs["pk"])

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return serializers.SubnetSerializerUpdate
        return serializers.SubnetSerializer


class InstanceTypeViewSet(drf_helpers.CustomReadOnlyModelViewSet):
    """
    List compute instance types in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.InstanceTypeSerializer
    lookup_value_regex = '[^/]+'

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.compute.instance_types.list()

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


class BlockStoreViewSet(drf_helpers.CustomReadOnlySingleViewSet):
    """
    List blockstore urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.BlockStoreSerializer


class VolumeViewSet(drf_helpers.CustomModelViewSet):
    """
    List volumes in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.VolumeSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.block_store.volumes.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.block_store.volumes.get(self.kwargs["pk"])
        return obj


class SnapshotViewSet(drf_helpers.CustomModelViewSet):
    """
    List snapshots in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.SnapshotSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.block_store.snapshots.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.block_store.snapshots.get(self.kwargs["pk"])
        return obj


class ObjectStoreViewSet(drf_helpers.CustomReadOnlySingleViewSet):
    """
    List compute related urls.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.ObjectStoreSerializer


class BucketViewSet(drf_helpers.CustomModelViewSet):
    """
    List buckets in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.BucketSerializer

    def list_objects(self):
        provider = view_helpers.get_cloud_provider(self)
        return provider.object_store.list()

    def get_object(self):
        provider = view_helpers.get_cloud_provider(self)
        obj = provider.object_store.get(self.kwargs["pk"])
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
        bucket = provider.object_store.get(bucket_pk)
        if bucket:
            return bucket.list()
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
        bucket = provider.object_store.get(bucket_pk)
        if bucket:
            return bucket.get(self.kwargs["pk"])
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
    permission_classes = [permissions.DjangoModelPermissions]

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
    permission_classes = [permissions.DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'userprofile'):
            return user.userprofile.credentials.filter(
                openstackcredentials__isnull=False).select_subclasses()
        return models.OpenStackCredentials.objects.none()


class DeploymentViewSet(viewsets.ModelViewSet):
    """
    List compute related urls.
    """
    queryset = models.ApplicationDeployment.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.DeploymentSerializer


class PublicServiceViewSet(viewsets.ModelViewSet):
    """
    List public services
    """
    queryset = models.PublicService.objects.all()
    serializer_class = serializers.PublicServiceSerializer

