from rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers
from rest_framework.reverse import reverse

from baselaunch import models


class ZoneSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class RegionSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField('detail_url')
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    zones = serializers.SerializerMethodField('zones_url')

    def detail_url(self, obj):
        """Create a URL for accessing a single instance."""
        return reverse('region-detail',
                       args=[self.context['cloud_pk'], obj.id],
                       request=self.context['request'])

    def zones_url(self, obj):
        """Include a URL for listing zones"""
        return reverse('zone-list', args=[self.context['cloud_pk'], obj.id],
                       request=self.context['request'])

    def __init__(self, *args, **kwargs):
        super(RegionSerializer, self).__init__(*args, **kwargs)
        # For the detail view, do not include the url field
        if not self.context.get('list', False):
            self.fields.pop('url')


class MachineImageSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField('detail_url')
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField()

    def detail_url(self, obj):
        """Create a URL for accessing a single instance."""
        return reverse('machine_image-detail',
                       args=[self.context['cloud_pk'], obj.id],
                       request=self.context['request'])

    def __init__(self, *args, **kwargs):
        super(MachineImageSerializer, self).__init__(*args, **kwargs)
        # For the detail view, do not include the url field
        if not self.context.get('list', False):
            self.fields.pop('url')


class KeyPairSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField('detail_url')
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    material = serializers.CharField()

    def detail_url(self, obj):
        """Create a URL for accessing a single instance."""
        return reverse('keypair-detail',
                       args=[self.context['cloud_pk'], obj.id],
                       request=self.context['request'])

    def __init__(self, *args, **kwargs):
        super(KeyPairSerializer, self).__init__(*args, **kwargs)
        # For the detail view, do not include the url field
        if not self.context.get('list', False):
            self.fields.pop('url')


class SecurityGroupRuleSerializer(serializers.Serializer):
    ip_protocol = serializers.CharField()
    from_port = serializers.CharField()
    to_port = serializers.CharField()
    cidr_ip = serializers.CharField()


class SecurityGroupSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField('detail_url')
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField()
    rules = serializers.SerializerMethodField('rules_url')

    def detail_url(self, obj):
        """Create a URL for accessing a single instance."""
        return reverse('security_group-detail',
                       args=[self.context['cloud_pk'], obj.id],
                       request=self.context['request'])

    def rules_url(self, obj):
        """Include a URL for listing this SG rules."""
        return reverse('security_group_rule-list', args=[self.context['cloud_pk'], obj.id],
                       request=self.context['request'])

    def __init__(self, *args, **kwargs):
        super(SecurityGroupSerializer, self).__init__(*args, **kwargs)
        # For the detail view, do not include the url field
        if not self.context.get('list', False):
            self.fields.pop('url')


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


class InstanceTypeSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField('detail_url')
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    family = serializers.CharField()
    vcpus = serializers.CharField()
    ram = serializers.CharField()
    size_root_disk = serializers.CharField()
    size_ephemeral_disks = serializers.CharField()
    num_ephemeral_disks = serializers.CharField()
    size_total_disk = serializers.CharField()
    extra_data = serializers.DictField(serializers.CharField())

    def detail_url(self, obj):
        """Create a URL for accessing a single instance."""
        slug = obj.name.replace('.', '_')  # slugify
        return reverse('instance_type-detail',
                       args=[self.context['cloud_pk'], slug],
                       request=self.context['request'])

    def __init__(self, *args, **kwargs):
        super(InstanceTypeSerializer, self).__init__(*args, **kwargs)
        # For the detail view, do not include the url field
        if not self.context.get('list', False):
            self.fields.pop('url')


class VolumeSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    state = serializers.CharField()


class SnapshotSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    state = serializers.CharField()


class InstanceSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField('detail_url')
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    public_ips = serializers.ListField(serializers.IPAddressField())
    private_ips = serializers.ListField(serializers.IPAddressField())
    instance_type = serializers.SerializerMethodField('instance_type_name')
    instance_type_url = serializers.SerializerMethodField('instance_type_link')
    image_id = serializers.CharField()
    image_id_url = serializers.SerializerMethodField('image_id_link')
    placement_zone = ZoneSerializer()

    def detail_url(self, obj):
        return reverse('instance-detail',
                       args=[self.context['cloud_pk'], obj.id],
                       request=self.context['request'])

    def instance_type_name(self, obj):
        """
        Include a URL for listing compute instance type for this instance.
        """
        return obj.instance_type.name

    def instance_type_link(self, obj):
        slug = (obj.instance_type.name).replace('.', '_')  # slugify
        return reverse('instance_type-detail',
                       args=[self.context['cloud_pk'], slug],
                       request=self.context['request'])

    def image_id_link(self, obj):
        return reverse('machine_image-detail',
                       args=[self.context['cloud_pk'], obj.image_id],
                       request=self.context['request'])

    def __init__(self, *args, **kwargs):
        super(InstanceSerializer, self).__init__(*args, **kwargs)
        # Grabbing instance type for OpenStack is slow because for each
        # instance, an additional request is made to retrieve the actual
        # instance type and this takes ages. Hence, display instance_type only
        # in detail view.
        if self.context.get('list', False):
            self.fields.pop('instance_type')
            self.fields.pop('instance_type_url')
        else:
            # For the detail view, do not include the url field
            self.fields.pop('url')


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
    machine_images = serializers.SerializerMethodField('machine_images_url')
    keypairs = serializers.SerializerMethodField('keypairs_url')
    security_groups = serializers.SerializerMethodField('security_groups_url')
    networks = serializers.SerializerMethodField('networks_url')
    instance_types = serializers.SerializerMethodField('instance_types_url')
    instances = serializers.SerializerMethodField('instances_url')
    volumes = serializers.SerializerMethodField('volume_url')
    snapshots = serializers.SerializerMethodField('snapshot_url')
    buckets = serializers.SerializerMethodField('bucket_url')

    def regions_url(self, obj):
        """
        Include a URL for listing regions within this cloud.
        """
        return reverse('region-list', args=[obj.slug],
                       request=self.context['request'])

    def machine_images_url(self, obj):
        """
        Include a URL for listing machine images within this cloud.
        """
        return reverse('machine_image-list', args=[obj.slug],
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

    def instance_types_url(self, obj):
        """
        Include a URL for listing compute instance types within this cloud.
        """
        return reverse('instance_type-list', args=[obj.slug],
                       request=self.context['request'])

    def instances_url(self, obj):
        """
        Include a URL for listing compute instances within this cloud.
        """
        return reverse('instance-list', args=[obj.slug],
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
        exclude = ('secret_key', )


class OpenStackCredsSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.OpenStackCredentials
        exclude = ('password', )


class UserSerializer(UserDetailsSerializer):
    aws_creds = serializers.SerializerMethodField()
    openstack_creds = serializers.SerializerMethodField()

    def get_aws_creds(self, obj):
        """
        Include a URL for listing this bucket's contents
        """
        creds = obj.userprofile.credentials.filter(
            awscredentials__isnull=False).select_subclasses()
        return AWSCredsSerializer(instance=creds, many=True).data

    def get_openstack_creds(self, obj):
        """
        Include a URL for listing this bucket's contents
        """
        creds = obj.userprofile.credentials.filter(
            openstackcredentials__isnull=False).select_subclasses()
        return OpenStackCredsSerializer(instance=creds, many=True).data

    class Meta(UserDetailsSerializer.Meta):
        fields = UserDetailsSerializer.Meta.fields + ('aws_creds',
                                                      'openstack_creds')
