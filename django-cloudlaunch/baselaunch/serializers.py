# from django.contrib.auth.models import User, Group
from rest_framework import serializers

from baselaunch import models


class AppVersionSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.ApplicationVersion
        fields = ('version', 'image_id', 'launch_data')


class ApplicationSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    versions = AppVersionSerializer(many=True, read_only=True)

    class Meta:
        model = models.Application


class CategorySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Category


class InfrastructureSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Infrastructure
        fields = ('url', 'name')


class AWSEC2Serializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.AWSEC2
        fields = InfrastructureSerializer.Meta.fields + ('region_name',)


class ImageSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Image
        # fields = ('url', 'name', 'image_id', 'description')
