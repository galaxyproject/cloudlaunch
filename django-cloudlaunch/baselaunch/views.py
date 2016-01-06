from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from baselaunch import models
from baselaunch import serializers


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


class InfrastructureList(APIView):
    """
    List kinds in infrastructures.
    """
    def get(self, request, format=None):
        # We only support cloud infrastructures for the time being
        response = {'url': request.build_absolute_uri('clouds')}
        return Response(response)


class CloudViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and or edit cloud infrastructure info.
    """
    queryset = models.Cloud.objects.all()
    serializer_class = serializers.CloudSerializer
