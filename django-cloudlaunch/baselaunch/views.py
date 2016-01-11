import json

from rest_framework import viewsets
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

    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.RegionSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.RegionSerializer(instance=provider.compute.regions.list(),
                                                  many=True)
        return Response(serializer.data)


class KeyPairViewSet(viewsets.ViewSet):
    """
    List keypairs in a given cloud.
    """

    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.KeyPairSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.KeyPairSerializer(instance=provider.security.key_pairs.list(),
                                                   many=True)
        return Response(serializer.data)


class BucketViewSet(viewsets.ViewSet):
    """
    List buckets in a given cloud.
    """

    # Required for the Browsable API renderer to have a nice form.
    serializer_class = serializers.BucketSerializer

    def list(self, request, **kwargs):
        provider = view_helpers.get_cloud_provider(self)
        serializer = serializers.BucketSerializer(instance=provider.object_store.list(),
                                                  many=True)
        return Response(serializer.data)
