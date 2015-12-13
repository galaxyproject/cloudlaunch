from django.contrib.auth.models import User, Group
from rest_framework import viewsets

from baselaunch import models
from baselaunch import serializers


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = models.Application.objects.all()
    serializer_class = serializers.ApplicationSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer


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


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = serializers.GroupSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = serializers.UserSerializer
