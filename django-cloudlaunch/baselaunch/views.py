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
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.RegionSerializer(
            instance=provider.compute.regions.list(),
            many=True,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': True})
        return Response(serializer.data)

    def retrieve(self, request, pk=None, cloud_pk=None):
        provider = view_helpers.get_cloud_provider(self)
        instance = provider.compute.regions.get(pk)
        if not instance:
            return Response({'detail': 'Cannot find region {0}'.format(
                             pk)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = serializers.RegionSerializer(
            instance=instance,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': False})
        return Response(serializer.data)


class MachineImageViewSet(viewsets.ViewSet):
    """
    List machine images in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.MachineImageSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.MachineImageSerializer(
            instance=provider.compute.images.list(),
            many=True,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': True})
        return Response(serializer.data)

    def retrieve(self, request, pk=None, cloud_pk=None):
        provider = view_helpers.get_cloud_provider(self)
        instance = provider.compute.images.get(pk)
        if not instance:
            return Response({'detail': 'Cannot find machine image {0}'.format(
                             pk)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = serializers.MachineImageSerializer(
            instance=instance,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': False})
        return Response(serializer.data)


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
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.KeyPairSerializer(
            instance=provider.security.key_pairs.list(), many=True,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': True})
        return Response(serializer.data)

    def retrieve(self, request, pk=None, cloud_pk=None):
        provider = view_helpers.get_cloud_provider(self)
        instance = provider.security.key_pairs.get(pk)
        if not instance:
            return Response({'detail': 'Cannot find key pair {0}'.format(
                             pk)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = serializers.KeyPairSerializer(
            instance=instance,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': False})
        return Response(serializer.data)


class SecurityGroupViewSet(viewsets.ViewSet):
    """
    List security groups in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.SecurityGroupSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.SecurityGroupSerializer(
            instance=provider.security.security_groups.list(), many=True,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': True})
        return Response(serializer.data)

    def retrieve(self, request, pk=None, cloud_pk=None):
        provider = view_helpers.get_cloud_provider(self)
        instance = provider.security.security_groups.get(pk)
        if not instance:
            return Response({'detail': 'Cannot find security group {0}'.format(
                             pk)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = serializers.SecurityGroupSerializer(
            instance=instance,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': False})
        return Response(serializer.data)


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
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.NetworkSerializer(
            instance=provider.network.list(), many=True,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk")})
        return Response(serializer.data)


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
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.InstanceTypeSerializer(
            instance=provider.compute.instance_types.list(), many=True,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': True})
        return Response(serializer.data)

    def retrieve(self, request, pk=None, cloud_pk=None):
        name = pk.replace('_', '.')  # un-slugify
        provider = view_helpers.get_cloud_provider(self)
        instance_types = provider.compute.instance_types.find(name=name)
        if len(instance_types) != 1:
            return Response({'detail': 'Cannot find instance type {0}'.format(
                             pk)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = serializers.InstanceTypeSerializer(
            instance=instance_types[0],
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
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.InstanceSerializer(
            instance=provider.compute.instances.list(), many=True,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': True})
        return Response(serializer.data)

    def retrieve(self, request, pk=None, cloud_pk=None):
        provider = view_helpers.get_cloud_provider(self)
        instance = provider.compute.instances.get(pk)
        if not instance:
            return Response({'detail': 'Cannot find instance {0}'.format(
                             pk)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = serializers.InstanceSerializer(
            instance=instance,
            context={'request': self.request,
                     'cloud_pk': self.kwargs.get("cloud_pk"),
                     'list': False})
        return Response(serializer.data)


class VolumeViewSet(viewsets.ViewSet):
    """
    List volumes in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.VolumeSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.VolumeSerializer(
            instance=provider.block_store.volumes.list(),
            many=True)
        return Response(serializer.data)


class SnapshotViewSet(viewsets.ViewSet):
    """
    List snapshots in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.SnapshotSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.SnapshotSerializer(
            instance=provider.block_store.snapshots.list(),
            many=True)
        return Response(serializer.data)


class BucketViewSet(viewsets.ViewSet):
    """
    List buckets in a given cloud.
    """
    permission_classes = (IsAuthenticated,)
    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.BucketSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.BucketSerializer(
            instance=provider.object_store.list(),
            many=True, context={'request': self.request,
                                'cloud_pk': self.kwargs.get("cloud_pk")})
        return Response(serializer.data)


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
