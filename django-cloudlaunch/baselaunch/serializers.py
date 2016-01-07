import urllib.parse
from rest_framework import serializers

from baselaunch import models


class CloudSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(read_only=True)
    regions = serializers.SerializerMethodField('regions_url')

    def regions_url(self, obj):
        """
        Include a URL for listing regions within this cloud.
        """
        rel_url = urllib.parse.urljoin(self.context['request'].path, 'regions')
        return self.context['request'].build_absolute_uri(rel_url)

    class Meta:
        model = models.Cloud
        fields = ("name", "slug", "regions")


class CloudImageSerializer(serializers.HyperlinkedModelSerializer):
    cloud = CloudSerializer(read_only=True, source='cloudimage.cloud')

    class Meta:
        model = models.CloudImage
        fields = ('name', 'cloud', 'image_id', 'description')


class AppVersionSerializer(serializers.HyperlinkedModelSerializer):
    images = CloudImageSerializer(many=True, read_only=True)

    class Meta:
        model = models.ApplicationVersion
        fields = ('version', 'images', 'launch_data')


class ApplicationSerializer(serializers.HyperlinkedModelSerializer):
    slug = serializers.CharField(read_only=True)
    versions = AppVersionSerializer(many=True, read_only=True)

    class Meta:
        model = models.Application


# class AWSSerializer(serializers.HyperlinkedModelSerializer):

#     class Meta:
#         model = models.AWS
#         # fields = CloudSerializer.Meta.fields + ('region_name',)
