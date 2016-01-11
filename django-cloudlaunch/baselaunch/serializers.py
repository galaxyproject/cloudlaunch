from rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers
from rest_framework.reverse import reverse

from baselaunch import models


class RegionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()


class KeyPairSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    material = serializers.CharField()


class CloudSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(read_only=True)
    regions = serializers.SerializerMethodField('regions_url')
    keypairs = serializers.SerializerMethodField('keypairs_url')

    def regions_url(self, obj):
        """
        Include a URL for listing regions within this cloud.
        """
        return reverse('region-list', args=[obj.slug],
                       request=self.context['request'])

    def keypairs_url(self, obj):
        """
        Include a URL for listing keypairs within this cloud.
        """
        return reverse('keypair-list', args=[obj.slug],
                       request=self.context['request'])

    class Meta:
        model = models.Cloud


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


class AWSCredsSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.AWSCredentials


class OpenStackCredsSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.OpenStackCredentials


class UserSerializer(UserDetailsSerializer):
    aws_creds = AWSCredsSerializer(
        many=True, read_only=True, source='userprofile.awscredentials_set')
    openstack_creds = OpenStackCredsSerializer(
        many=True, read_only=True,
        source='userprofile.openstackcredentials_set')

    class Meta(UserDetailsSerializer.Meta):
        fields = UserDetailsSerializer.Meta.fields + ('aws_creds',
                                                      'openstack_creds')
