# from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework.response import Response

from baselaunch import models
from baselaunch import serializers


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = models.Application.objects.all()
    serializer_class = serializers.ApplicationSerializer


class CategoryViewSet(viewsets.ViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer

    def list(self, request, pk=None, application_pk=None):
        categories = self.queryset.filter(application=application_pk)
        serializer = serializers.CategorySerializer(categories, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        categories = self.queryset.get(slug=pk)
        serializer = serializers.CategorySerializer(categories, context={'request': request})
        return Response(serializer.data)


class AWSEC2ViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows AWS EC2 cloud info to be viewed or edited.
    """
    queryset = models.AWSEC2.objects.all()
    serializer_class = serializers.AWSEC2Serializer


class InfrastructureViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows infrastructure info to be viewed or edited.
    """
    queryset = models.Infrastructure.objects.all()
    serializer_class = serializers.InfrastructureSerializer


class ImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows image info to be viewed or edited.
    """
    queryset = models.Image.objects.all()
    serializer_class = serializers.ImageSerializer
