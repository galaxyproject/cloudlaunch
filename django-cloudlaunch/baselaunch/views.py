from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from baselaunch import models
from baselaunch import serializers
from baselaunch import view_helpers


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = models.Application.objects.all()
    serializer_class = serializers.ApplicationSerializer


# class AWSEC2ViewSet(viewsets.ModelViewSet):
#     """
#     API endpoint that allows AWS EC2 cloud info to be viewed or edited.
#     """
#     queryset = models.AWSEC2.objects.all()
#     serializer_class = serializers.AWSEC2Serializer


# class ImageViewSet(viewsets.ModelViewSet):
#     """
#     API endpoint that allows image info to be viewed or edited.
#     """
#     queryset = models.CloudImage.objects.all()
#     serializer_class = serializers.CloudImageSerializer


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


class RegionViewSet(viewsets.ViewSet):
    """
    List regions in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.RegionSerializer

    def list(self, request, **kwargs):
        return view_helpers.generic_list(self, 'compute.regions',
                                         'RegionSerializer')

    def retrieve(self, request, pk=None, cloud_pk=None):
        return view_helpers.generic_retrieve(
            self, 'region', 'compute.regions', pk, 'RegionSerializer',
            cloud_pk)


class MachineImageViewSet(viewsets.ViewSet):
    """
    List machine images in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.MachineImageSerializer

    def list(self, request, **kwargs):
        return view_helpers.generic_list(self, 'compute.images',
                                         'MachineImageSerializer')

    def retrieve(self, request, pk=None, cloud_pk=None):
        return view_helpers.generic_retrieve(
            self, 'machine image', 'compute.images', pk,
            'MachineImageSerializer', cloud_pk)


class ZoneViewSet(viewsets.ViewSet):
    """
    List zones in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.ZoneSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        region_pk = self.kwargs.get("region_pk")
        region = provider.compute.regions.get(region_pk)
        if region:
            serializer = serializers.ZoneSerializer(region.zones,
                                                    many=True)
            return Response(serializer.data)
        else:
            return Response({})


class KeyPairViewSet(viewsets.ViewSet):
    """
    List key pairs in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.KeyPairSerializer

    def list(self, request, **kwargs):
        return view_helpers.generic_list(self, 'security.key_pairs',
                                         'KeyPairSerializer')

    def retrieve(self, request, pk=None, cloud_pk=None):
        return view_helpers.generic_retrieve(
            self, 'key pair', 'security.key_pairs', pk, 'KeyPairSerializer',
            cloud_pk)

    def create(self, request, cloud_pk, format=None):
        return view_helpers.generic_create(self, request.data,
                                           'KeyPairSerializer')

    def delete(self, request, pk, cloud_pk, format=None):
        provider = view_helpers.get_cloud_provider(self)
        kp = provider.security.key_pairs.get(pk)
        try:
            kp.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class SecurityGroupViewSet(viewsets.ViewSet):
    """
    List security groups in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.SecurityGroupSerializer

    def list(self, request, **kwargs):
        return view_helpers.generic_list(self, 'security.security_groups',
                                         'SecurityGroupSerializer')

    def retrieve(self, request, pk=None, cloud_pk=None):
        return view_helpers.generic_retrieve(
            self, 'security group', 'security.security_groups', pk,
            'SecurityGroupSerializer', cloud_pk)


class SecurityGroupRuleViewSet(viewsets.ViewSet):
    """
    List security group rules in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.SecurityGroupRuleSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        sg_pk = self.kwargs.get("security_group_pk")
        sg = provider.security.security_groups.get(sg_pk)
        serializer = serializers.SecurityGroupRuleSerializer(
            instance=sg.rules, many=True)
        return Response(serializer.data)


class NetworkViewSet(viewsets.ViewSet):
    """
    List networks in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.NetworkSerializer

    def list(self, request, **kwargs):
        return view_helpers.generic_list(self, 'network', 'NetworkSerializer')

    def retrieve(self, request, pk=None, cloud_pk=None):
        return view_helpers.generic_retrieve(
            self, 'network', 'network', pk, 'NetworkSerializer', cloud_pk)


class SubnetViewSet(viewsets.ViewSet):
    """
    List networks in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.SubnetSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        network_pk = self.kwargs.get("network_pk")
        network = provider.network.get(network_pk)
        serializer = serializers.SubnetSerializer(
            instance=network.subnets(), many=True)
        return Response(serializer.data)


class InstanceTypeViewSet(viewsets.ViewSet):
    """
    List compute instance types in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.InstanceTypeSerializer

    def list(self, request, **kwargs):
        return view_helpers.generic_list(self, 'compute.instance_types',
                                         'InstanceTypeSerializer')

    def retrieve(self, request, pk=None, cloud_pk=None):
        pk = pk.replace('_', '.')  # un-slugify
        provider = view_helpers.get_cloud_provider(self)
        instance_type = provider.compute.instance_types.get(pk)
        if not instance_type:
            return Response({'detail': 'Cannot find instance type {0}'.format(
                             pk)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = serializers.InstanceTypeSerializer(
            instance=instance_type,
            context={'request': self.request, 'cloud_pk': cloud_pk,
                     'list': False})
        return Response(serializer.data)


class InstanceViewSet(viewsets.ViewSet):
    """
    List compute instances in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.InstanceSerializer

    def list(self, request, **kwargs):
        return view_helpers.generic_list(self, 'compute.instances',
                                         'InstanceSerializer')

    def retrieve(self, request, pk=None, cloud_pk=None):
        return view_helpers.generic_retrieve(
            self, 'instance', 'compute.instances', pk, 'InstanceSerializer',
            cloud_pk)


class VolumeViewSet(viewsets.ViewSet):
    """
    List volumes in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.VolumeSerializer

    def list(self, request, **kwargs):
        return view_helpers.generic_list(self, 'block_store.volumes',
                                         'VolumeSerializer')

    def retrieve(self, request, pk=None, cloud_pk=None):
        return view_helpers.generic_retrieve(
            self, 'volume', 'block_store.volumes', pk, 'VolumeSerializer',
            cloud_pk)


class SnapshotViewSet(viewsets.ViewSet):
    """
    List snapshots in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.SnapshotSerializer

    def list(self, request, **kwargs):
        return view_helpers.generic_list(self, 'block_store.snapshots',
                                         'SnapshotSerializer')

    def retrieve(self, request, pk=None, cloud_pk=None):
        return view_helpers.generic_retrieve(
            self, 'snapshot', 'block_store.snapshots', pk,
            'SnapshotSerializer', cloud_pk)


class BucketViewSet(viewsets.ViewSet):
    """
    List buckets in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.BucketSerializer

    def list(self, request, **kwargs):
        return view_helpers.generic_list(self, 'object_store',
                                         'BucketSerializer')

    def retrieve(self, request, pk=None, cloud_pk=None):
        return view_helpers.generic_retrieve(
            self, 'bucket', 'object_store', pk, 'BucketSerializer', cloud_pk)


class BucketObjectViewSet(viewsets.ViewSet):
    """
    List objects in a given cloud bucket.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.BucketObjectSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        bucket_pk = self.kwargs.get("bucket_pk")
        bucket = provider.object_store.get(bucket_pk)
        if bucket:
            serializer = serializers.BucketObjectSerializer(bucket.list(),
                                                            many=True)
            return Response(serializer.data)
        else:
            return Response({})
