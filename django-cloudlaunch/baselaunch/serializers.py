from rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers

from baselaunch import models
from baselaunch import view_helpers
from baselaunch.drf_helpers import CustomHyperlinkedIdentityField
from baselaunch.drf_helpers import ProviderPKRelatedField


class ZoneSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class RegionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='region-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    zones = CustomHyperlinkedIdentityField(view_name='zone-list',
                                           lookup_field='id',
                                           lookup_url_kwarg='region_pk',
                                           parent_url_kwargs=['cloud_pk'])


class MachineImageSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='machine_image-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    description = serializers.CharField()


class KeyPairSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='keypair-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    material = serializers.CharField(read_only=True)

    def create(self, validated_data):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        return provider.security.key_pairs.create(validated_data.get('name'))


class SecurityGroupRuleSerializer(serializers.Serializer):
    ip_protocol = serializers.CharField(label="IP protocol")
    from_port = serializers.CharField()
    to_port = serializers.CharField()
    cidr_ip = serializers.CharField(label="CIDR IP")

    def create(self, validated_data):

        class SGRule(object):
            """
            A template for a Security Group Rule.

            This is necessary unless a specific security group rule can be
            retrieved via CloudBridge (i.e., ``SecurityGroupRuleService``
            is added).
            """

            def __init__(self, ip_protocol, from_port, to_port, cidr_ip=None):
                self.ip_protocol = ip_protocol
                self.from_port = from_port
                self.to_port = to_port
                self.cidr_ip = cidr_ip

        view = self.context.get('view')
        provider = view_helpers.get_cloud_provider(view)
        sg_pk = view.kwargs.get('security_group_pk')
        if sg_pk:
            sg = provider.security.security_groups.get(sg_pk)
            if sg and sg.add_rule(validated_data.get('ip_protocol'),
                                  validated_data.get('from_port'),
                                  validated_data.get('to_port'),
                                  validated_data.get('cidr_ip')):
                return SGRule(validated_data.get('ip_protocol'),
                              validated_data.get('from_port'),
                              validated_data.get('to_port'),
                              validated_data.get('cidr_ip'))
        return None


class SecurityGroupSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='security_group-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    # Technically, the description is required but when wanting to reuse an
    # existing security group with a different resource (eg, creating an
    # instance), we need to be able to call this serializer w/o it.
    description = serializers.CharField(required=False)
    rules = CustomHyperlinkedIdentityField(view_name='security_group_rule-list',
                                           lookup_field='id',
                                           lookup_url_kwarg='security_group_pk',
                                           parent_url_kwargs=['cloud_pk'])

    def create(self, validated_data):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        return provider.security.security_groups.create(
            validated_data.get('name'), validated_data.get('description'))


class NetworkSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='network-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    state = serializers.CharField(read_only=True)
    cidr_block = serializers.CharField(read_only=True)
    subnets = CustomHyperlinkedIdentityField(view_name='subnet-list',
                                             lookup_field='id',
                                             lookup_url_kwarg='network_pk',
                                             parent_url_kwargs=['cloud_pk'])

    def create(self, validated_data):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        return provider.network.create(name=validated_data.get('name'))

    def update(self, instance, validated_data):
        try:
            if instance.name != validated_data.get('name'):
                instance.name = validated_data.get('name')
            return instance
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))


class SubnetSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='subnet-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk',
                                                            'network_pk'])
    name = serializers.CharField(allow_blank=True)
    cidr_block = serializers.CharField()
    network_id = serializers.CharField(read_only=True)

    def create(self, validated_data):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        net_id = self.context.get('view').kwargs.get('network_pk')
        return provider.network.subnets.create(
            net_id, validated_data.get('cidr_block'),
            name=validated_data.get('name'))


class SubnetSerializerUpdate(SubnetSerializer):
    cidr_block = serializers.CharField(read_only=True)

    def update(self, instance, validated_data):
        try:
            if instance.name != validated_data.get('name'):
                instance.name = validated_data.get('name')
            return instance
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))


class InstanceTypeSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='instance_type-detail',
                                         lookup_field='name',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    family = serializers.CharField()
    vcpus = serializers.CharField()
    ram = serializers.CharField()
    size_root_disk = serializers.CharField()
    size_ephemeral_disks = serializers.CharField()
    num_ephemeral_disks = serializers.CharField()
    size_total_disk = serializers.CharField()
    extra_data = serializers.DictField(serializers.CharField())


class AttachmentInfoSerializer(serializers.Serializer):
    device = serializers.CharField(read_only=True)
    instance_id = ProviderPKRelatedField(label="Instance ID",
                                         queryset='compute.instances',
                                         display_fields=[
                                             'name', 'id'],
                                         display_format="{0} (ID: {1})",
                                         required=False,
                                         allow_null=True)

    instance = CustomHyperlinkedIdentityField(view_name='instance-detail',
                                              lookup_field='instance_id',
                                              lookup_url_kwarg='pk',
                                              parent_url_kwargs=['cloud_pk'])


class VolumeSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='volume-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    size = serializers.IntegerField(min_value=0)
    create_time = serializers.CharField(read_only=True)
    zone = serializers.CharField(source='zone_id')
    state = serializers.CharField(read_only=True)
    snapshot_id = ProviderPKRelatedField(label="Snapshot ID",
                                         queryset='block_store.snapshots',
                                         display_fields=[
                                             'name', 'id', 'size'],
                                         display_format="{0} (ID: {1},"
                                         " Size: {2} GB)",
                                         write_only=True,
                                         required=False,
                                         allow_null=True)

    attachments = AttachmentInfoSerializer()

    def create(self, validated_data):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        try:
            return provider.block_store.volumes.create(
                validated_data.get('name'),
                validated_data.get('size'),
                validated_data.get('zone_id'),
                description=validated_data.get('description'),
                snapshot=validated_data.get('snapshot_id'))
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))

    def update(self, instance, validated_data):
        try:
            if instance.name != validated_data.get('name'):
                instance.name = validated_data.get('name')
            if instance.description != validated_data.get('description'):
                instance.description = validated_data.get('description')
            return instance
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))


class SnapshotSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='snapshot-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    description = serializers.CharField()
    state = serializers.CharField(read_only=True)
    volume_id = ProviderPKRelatedField(label="Volume ID",
                                       queryset='block_store.volumes',
                                       display_fields=[
                                             'name', 'id', 'size'],
                                       display_format="{0} (ID: {1},"
                                       " Size: {2} GB)",
                                       required=True)
    create_time = serializers.CharField(read_only=True)
    size = serializers.IntegerField(min_value=0, read_only=True)

    def create(self, validated_data):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        try:
            return provider.block_store.snapshots.create(
                validated_data.get('name'),
                validated_data.get('volume_id'),
                description=validated_data.get('description'))
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))

    def update(self, instance, validated_data):
        try:
            if instance.name != validated_data.get('name'):
                instance.name = validated_data.get('name')
            if instance.description != validated_data.get('description'):
                instance.description = validated_data.get('description')
            return instance
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))


class InstanceSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='instance-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    public_ips = serializers.ListField(serializers.IPAddressField())
    private_ips = serializers.ListField(serializers.IPAddressField())
    instance_type = serializers.CharField(source='instance_type.name')
    instance_type_url = CustomHyperlinkedIdentityField(view_name='instance-detail',
                                                       lookup_field='instance_type.id',
                                                       lookup_url_kwarg='pk',
                                                       parent_url_kwargs=['cloud_pk'])
    image_id = serializers.CharField(read_only=True)
    image_id_url = CustomHyperlinkedIdentityField(view_name='machine_image-detail',
                                                  lookup_field='image_id',
                                                  lookup_url_kwarg='pk',
                                                  parent_url_kwargs=['cloud_pk'])
    key_pair_name = serializers.CharField()
    placement_zone = ZoneSerializer()
    security_groups = SecurityGroupSerializer(many=True)

    def __init__(self, *args, **kwargs):
        super(InstanceSerializer, self).__init__(*args, **kwargs)
        # Grabbing the following fields for OpenStack is slow because for each
        # instance, an additional request is made to retrieve the actual
        # data and this takes ages. Hence, display full details only
        # in detail view.
        if isinstance(self.instance, list):
            self.fields.pop('instance_type')
            self.fields.pop('instance_type_url')
            self.fields.pop('security_groups')

    def create(self, validated_data):
        # provider = view_helpers.get_cloud_provider(self.context.get('view'))
        print('validated_data: %s' % validated_data)
        # return provider.compute.instances.create()


class BucketSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='bucket-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    contents = CustomHyperlinkedIdentityField(view_name='object-list',
                                              lookup_field='id',
                                              lookup_url_kwarg='bucket_pk',
                                              parent_url_kwargs=['cloud_pk'])

    def create(self, validated_data):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        try:
            return provider.object_store.create(validated_data.get('name'))
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))


class BucketObjectSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()


class CloudSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(read_only=True)
    compute = CustomHyperlinkedIdentityField(view_name='compute-list',
                                             lookup_field='slug',
                                             lookup_url_kwarg='cloud_pk')
    security = CustomHyperlinkedIdentityField(view_name='security-list',
                                              lookup_field='slug',
                                              lookup_url_kwarg='cloud_pk')
    block_store = CustomHyperlinkedIdentityField(view_name='block_store-list',
                                                 lookup_field='slug',
                                                 lookup_url_kwarg='cloud_pk')
    object_store = CustomHyperlinkedIdentityField(view_name='object_store-list',
                                                  lookup_field='slug',
                                                  lookup_url_kwarg='cloud_pk')
    networks = CustomHyperlinkedIdentityField(view_name='network-list',
                                              lookup_field='slug',
                                              lookup_url_kwarg='cloud_pk')

    class Meta:
        model = models.Cloud
        exclude = ('kind',)


class ComputeSerializer(serializers.Serializer):
    machine_images = CustomHyperlinkedIdentityField(view_name='machine_image-list',
                                                    parent_url_kwargs=['cloud_pk'])
    instance_types = CustomHyperlinkedIdentityField(view_name='instance_type-list',
                                                    parent_url_kwargs=['cloud_pk'])
    instances = CustomHyperlinkedIdentityField(view_name='instance-list',
                                               parent_url_kwargs=['cloud_pk'])
    regions = CustomHyperlinkedIdentityField(view_name='region-list',
                                             parent_url_kwargs=['cloud_pk'])


class SecuritySerializer(serializers.Serializer):
    keypairs = CustomHyperlinkedIdentityField(view_name='keypair-list',
                                              parent_url_kwargs=['cloud_pk'])
    security_groups = CustomHyperlinkedIdentityField(view_name='security_group-list',
                                                     parent_url_kwargs=['cloud_pk'])


class BlockStoreSerializer(serializers.Serializer):
    volumes = CustomHyperlinkedIdentityField(view_name='volume-list',
                                             parent_url_kwargs=['cloud_pk'])
    snapshots = CustomHyperlinkedIdentityField(view_name='snapshot-list',
                                               parent_url_kwargs=['cloud_pk'])


class ObjectStoreSerializer(serializers.Serializer):
    buckets = CustomHyperlinkedIdentityField(view_name='bucket-list',
                                             parent_url_kwargs=['cloud_pk'])


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
        try:
            creds = obj.userprofile.credentials.filter(
                awscredentials__isnull=False).select_subclasses()
            return AWSCredsSerializer(instance=creds, many=True).data
        except models.UserProfile.DoesNotExist:
            return ""

    def get_openstack_creds(self, obj):
        """
        Include a URL for listing this bucket's contents
        """
        try:
            creds = obj.userprofile.credentials.filter(
                openstackcredentials__isnull=False).select_subclasses()
            return OpenStackCredsSerializer(instance=creds, many=True).data
        except models.UserProfile.DoesNotExist:
            return ""

    class Meta(UserDetailsSerializer.Meta):
        fields = UserDetailsSerializer.Meta.fields + ('aws_creds',
                                                      'openstack_creds')
