from rest_framework import serializers
from rest_framework.reverse import reverse

from baselaunch import models


class RegionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()


class CloudSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(read_only=True)
    regions = serializers.SerializerMethodField('regions_url')

    def regions_url(self, obj):
        """
        Include a URL for listing regions within this cloud.
        """
        return reverse('region-list', args=[obj.slug],
                       request=self.context['request'])

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
