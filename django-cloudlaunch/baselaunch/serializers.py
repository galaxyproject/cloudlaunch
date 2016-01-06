from rest_framework import serializers

from baselaunch import models


class AppVersionSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.ApplicationVersion
        fields = ('version', 'image_id', 'launch_data')


class ApplicationSerializer(serializers.HyperlinkedModelSerializer):
    slug = serializers.CharField(read_only=True)
    versions = AppVersionSerializer(many=True, read_only=True)

    class Meta:
        model = models.Application


class InfrastructureSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Infrastructure
        fields = ('url', 'name')


class CloudSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Cloud


class AWSEC2Serializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.AWSEC2
        fields = InfrastructureSerializer.Meta.fields + ('region_name',)


class ImageSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Image
        # fields = ('url', 'name', 'image_id', 'description')
