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


class SecurityGroupRuleSerializer(serializers.Serializer):
    ip_protocol = serializers.CharField()
    from_port = serializers.CharField()
    to_port = serializers.CharField()
    cidr_ip = serializers.CharField()


class SecurityGroupSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField()
    rules = serializers.SerializerMethodField('rules_url')

    def rules_url(self, obj):
        """Include a URL for listing this SG rules."""
        return reverse('security_group_rule-list', args=[self.context['cloud_pk'], obj.id],
                       request=self.context['request'])


class NetworkSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    state = serializers.CharField()
    cidr_block = serializers.CharField()
    subnets = serializers.SerializerMethodField('subnets_url')

    def subnets_url(self, obj):
        """Include a URL for listing this network subnets."""
        return reverse('subnet-list', args=[self.context['cloud_pk'], obj.id],
                       request=self.context['request'])


class SubnetSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    cidr_block = serializers.CharField()


class VolumeSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    state = serializers.CharField()


class SnapshotSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    state = serializers.CharField()


class BucketSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    contents = serializers.SerializerMethodField('content_url')

    def content_url(self, obj):
        """
        Include a URL for listing this bucket's contents
        """
        return reverse('object-list', args=[self.context['cloud_pk'], obj.id],
                       request=self.context['request'])


class BucketObjectSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()


class CloudSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(read_only=True)
    regions = serializers.SerializerMethodField('regions_url')
    keypairs = serializers.SerializerMethodField('keypairs_url')
    security_groups = serializers.SerializerMethodField('security_groups_url')
    networks = serializers.SerializerMethodField('networks_url')
    volumes = serializers.SerializerMethodField('volume_url')
    snapshots = serializers.SerializerMethodField('snapshot_url')
    buckets = serializers.SerializerMethodField('bucket_url')

    def regions_url(self, obj):
        """
        Include a URL for listing regions within this cloud.
        """
        return reverse('region-list', args=[obj.slug],
                       request=self.context['request'])

    def keypairs_url(self, obj):
        """
        Include a URL for listing key pairs within this cloud.
        """
        return reverse('keypair-list', args=[obj.slug],
                       request=self.context['request'])

    def security_groups_url(self, obj):
        """
        Include a URL for listing security groups within this cloud.
        """
        return reverse('security_group-list', args=[obj.slug],
                       request=self.context['request'])

    def networks_url(self, obj):
        """
        Include a URL for listing networks within this cloud.
        """
        return reverse('network-list', args=[obj.slug],
                       request=self.context['request'])

    def volume_url(self, obj):
        """
        Include a URL for listing volumes within this cloud.
        """
        return reverse('volume-list', args=[obj.slug],
                       request=self.context['request'])

    def snapshot_url(self, obj):
        """
        Include a URL for listing snapshots within this cloud.
        """
        return reverse('snapshot-list', args=[obj.slug],
                       request=self.context['request'])

    def bucket_url(self, obj):
        """
        Include a URL for listing buckets within this cloud.
        """
        return reverse('bucket-list', args=[obj.slug],
                       request=self.context['request'])

    class Meta:
        model = models.Cloud
        exclude = ('kind',)


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
