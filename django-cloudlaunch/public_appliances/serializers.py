from rest_framework import serializers

from django_countries.serializer_fields import CountryField

from . import models



### Public Services Serializers ###
class LocationSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="pubapp:location-detail",
    )
    country = CountryField(country_dict=True)

    class Meta:
        model = models.Location
        fields = '__all__'


class SponsorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Sponsor
        fields = '__all__'


class PublicServiceSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="pubapp:publicservice-detail",
    )
   
    location = LocationSerializer(read_only=True)

    class Meta:
        model = models.PublicService
        fields = '__all__'
