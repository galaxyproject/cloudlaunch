from rest_framework import viewsets

from . import models
from . import serializers


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

