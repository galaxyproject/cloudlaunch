import urllib
import json
import jsonmerge
import yaml

from rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers
from rest_framework.reverse import reverse

from baselaunch import models
from baselaunch import tasks
from baselaunch import view_helpers
from baselaunch.drf_helpers import CustomHyperlinkedIdentityField
from baselaunch.drf_helpers import PlacementZonePKRelatedField
from baselaunch.drf_helpers import ProviderPKRelatedField
from django.contrib.sessions.serializers import JSONSerializer


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
    ip_protocol = serializers.CharField(label="IP protocol", allow_blank=True)
    from_port = serializers.CharField(allow_blank=True)
    to_port = serializers.CharField(allow_blank=True)
    cidr_ip = serializers.CharField(label="CIDR IP", allow_blank=True)
    group = ProviderPKRelatedField(label="Source group",
                                   queryset='security.security_groups',
                                   display_fields=['name', 'id'],
                                   display_format="{0} (ID: {1})",
                                   required=False,
                                   allow_null=True)
    url = CustomHyperlinkedIdentityField(view_name='security_group_rule-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk',
                                                            'security_group_pk'])

    def create(self, validated_data):
        view = self.context.get('view')
        provider = view_helpers.get_cloud_provider(view)
        sg_pk = view.kwargs.get('security_group_pk')
        if sg_pk:
            sg = provider.security.security_groups.get(sg_pk)
            if sg and validated_data.get('group'):
                return sg.add_rule(src_group=validated_data.get('group'))
            elif sg:
                return sg.add_rule(validated_data.get('ip_protocol'),
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
                                         lookup_field='pk',
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
    zone_id = PlacementZonePKRelatedField(label="Zone",
                                          queryset='non_empty_value',
                                          display_fields=[
                                              'id'],
                                          display_format="{0}",
                                          required=True)
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
    instance_type_id = ProviderPKRelatedField(label="Instance Type",
                                              queryset='compute.instance_types',
                                              display_fields=[
                                                  'name'],
                                              display_format="{0}",
                                              required=True)
    instance_type_url = CustomHyperlinkedIdentityField(view_name='instance_type-detail',
                                                       lookup_field='instance_type_id',
                                                       lookup_url_kwarg='pk',
                                                       parent_url_kwargs=['cloud_pk'])
    image_id = ProviderPKRelatedField(label="Image",
                                      queryset='compute.images',
                                      display_fields=[
                                               'name', 'id'],
                                      display_format="{0} ({1})",
                                      required=True)
    image_id_url = CustomHyperlinkedIdentityField(view_name='machine_image-detail',
                                                  lookup_field='image_id',
                                                  lookup_url_kwarg='pk',
                                                  parent_url_kwargs=['cloud_pk'])
    key_pair_name = ProviderPKRelatedField(label="Keypair Name",
                                           queryset='security.key_pairs',
                                           display_fields=[
                                               'id'],
                                           display_format="{0}",
                                           required=True)
    zone_id = PlacementZonePKRelatedField(label="Placement Zone",
                                          queryset='non_empty_value',
                                          display_fields=[
                                              'id'],
                                          display_format="{0}",
                                          required=True)
    security_group_ids = ProviderPKRelatedField(label="Security Groups",
                                                queryset='security.security_groups',
                                                display_fields=[
                                                    'name'],
                                                display_format="{0}",
                                                many=True)
    user_data = serializers.CharField(write_only=True,
                                      style={'base_template': 'textarea.html'})

    def create(self, validated_data):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        name = validated_data.get('name')
        image_id = validated_data.get('image_id')
        instance_type = validated_data.get('instance_type_id')
        kp_name = validated_data.get('key_pair_name')
        zone_id = validated_data.get('zone_id')
        security_group_ids = validated_data.get('security_group_ids')
        user_data = validated_data.get('user_data')
        try:
            return provider.compute.instances.create(
                name, image_id, instance_type, zone=zone_id, key_pair=kp_name,
                security_groups=security_group_ids, user_data=user_data)
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))

    def update(self, instance, validated_data):
        try:
            if instance.name != validated_data.get('name'):
                instance.name = validated_data.get('name')
            return instance
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))


class BucketSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='bucket-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    objects = CustomHyperlinkedIdentityField(view_name='bucketobject-list',
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
    name = serializers.CharField(allow_blank=True)
    size = serializers.IntegerField(read_only=True)
    last_modified = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='bucketobject-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk', 'bucket_pk'])
    download_url = serializers.SerializerMethodField()
    upload_content = serializers.FileField(write_only=True)

    def get_download_url(self, obj):
        """Create a URL for accessing a single instance."""
        kwargs = self.context['view'].kwargs.copy()
        kwargs.update({'pk': obj.id})
        obj_url = reverse('bucketobject-detail',
                          kwargs=kwargs,
                          request=self.context['request'])
        return urllib.parse.urljoin(obj_url, '?format=binary')

    def create(self, validated_data):
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
        bucket_id = self.context.get('view').kwargs.get('bucket_pk')
        bucket = provider.object_store.get(bucket_id)
        try:
            name = validated_data.get('name')
            content = validated_data.get('upload_content')
            if name:
                object = bucket.create_object(name)
            else:
                object = bucket.create_object(content.name)
            if content:
                object.upload(content.file.getvalue())
            return object
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))

    def update(self, instance, validated_data):
        try:
            instance.upload(
                validated_data.get('upload_content').file.getvalue())
            return instance
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))


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

    region_name = serializers.SerializerMethodField()

    def get_region_name(self, obj):
        if hasattr(obj, 'aws'):
            return obj.aws.compute.ec2_region_name
        elif hasattr(obj, 'openstack'):
            return obj.openstack.region_name
        else:
            return "Cloud provider not recognized"

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

    class Meta:
        model = models.CloudImage
        fields = ('name', 'cloud', 'image_id', 'description')


class StringToJSONField(serializers.JSONField):
    def __init__(self, *args, **kwargs):
        super(StringToJSONField, self).__init__(*args, **kwargs)

    def to_representation(self, value):
        if value:
            return json.loads(value)
        else:
            return value


class AppVersionCloudConfigSerializer(serializers.HyperlinkedModelSerializer):


    cloud = CloudSerializer(read_only=True)
    image = CloudImageSerializer(read_only=True)
    default_launch_config = StringToJSONField()

    class Meta:
        model = models.ApplicationVersionCloudConfig
        fields = ('cloud', 'image', 'default_launch_config', 'default_instance_type')


class AppVersionSerializer(serializers.HyperlinkedModelSerializer):
    cloud_config = AppVersionCloudConfigSerializer(many=True, read_only=True, source='app_version_config')

    class Meta:
        model = models.ApplicationVersion
        fields = ('version','cloud_config', 'frontend_component_path', 'frontend_component_name')


class ApplicationSerializer(serializers.HyperlinkedModelSerializer):
    slug = serializers.CharField(read_only=True)
    versions = AppVersionSerializer(many=True, read_only=True)

    class Meta:
        model = models.Application


class DeploymentSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(read_only=True)
    name = serializers.CharField(required=False)
    instance_type = serializers.CharField(read_only=True)
    placement_zone = serializers.CharField(read_only=True)
    keypair_name = serializers.CharField(read_only=True)
    network = serializers.CharField(read_only=True)
    subnet = serializers.CharField(read_only=True)
    provider_settings = serializers.CharField(read_only=True)
    application_config = serializers.CharField(read_only=True)
    application = serializers.CharField(write_only=True, required=True)
    config_cloudlaunch = serializers.JSONField(write_only=True, required=True)
    config_app = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = models.ApplicationDeployment
        fields = ('id','name', 'application', 'application_version', 'target_cloud', 'instance_type',
                  'placement_zone', 'keypair_name', 'network', 'subnet', 'provider_settings',
                  'application_config', 'added', 'updated', 'owner', 'config_cloudlaunch', 'config_app')

    def to_internal_value(self, data):
        application = data.get('application')
        version = data.get('application_version')
        if version:
            version = models.ApplicationVersion.objects.get(application=application, version=version)
            data['application_version'] = version.id
        return super(DeploymentSerializer, self).to_internal_value(data)

    def import_class(self, name):
        """
        TODO: Move out to a different util class
        """
        from importlib import import_module

        parts = name.rsplit('.', 1)
        cls = getattr(import_module(parts[0]), parts[1])
        return cls

    def create(self, validated_data):
        cloud = validated_data.get("target_cloud")
        version = validated_data.get("application_version")
        launch_config = validated_data.get("config_cloudlaunch")
        cloud_version_config = models.ApplicationVersionCloudConfig.objects.get(application_version=version.id, cloud=cloud.slug)
        default_config = json.loads(cloud_version_config.default_launch_config)
        provider = view_helpers.get_cloud_provider(self.context.get('view'), cloud.slug)
        try:
            # print("validated_data: %s" % validated_data)
            # Task outline
            handler = self.import_class(version.backend_component_name)()
            app_config = validated_data.get("config_app", {})
            # print ("app_config: %s" % app_config)
            merged_config = jsonmerge.merge(default_config.get("config_app", {}), app_config)
            # print ("merged_config: %s" % merged_config)
            final_ud_config = handler.process_config_data(merged_config)
            print("--------------------------------")
            celery_task_id = tasks.launch_appliance(
                provider, cloud_version_config, launch_config, final_ud_config)
            #celery_task_id = tasks.launch_appliance(provider, deployment_model, user_data)
            #deployment_model.celery_task_id = celery_task_id
            return validated_data
        except Exception as e:
            raise serializers.ValidationError("{0}".format(e))


class CredentialsSerializer(serializers.Serializer):
    aws = CustomHyperlinkedIdentityField(view_name='awscredentials-list')
    openstack = CustomHyperlinkedIdentityField(
        view_name='openstackcredentials-list')


class AWSCredsSerializer(serializers.HyperlinkedModelSerializer):

    secret_key = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True,
        required=False
    )

    class Meta:
        model = models.AWSCredentials
        exclude = ('secret_key', 'user_profile')


class OpenstackCredsSerializer(serializers.HyperlinkedModelSerializer):

    password = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True,
        required=False
    )

    class Meta:
        model = models.OpenStackCredentials
        exclude = ('password', 'user_profile')


class UserSerializer(UserDetailsSerializer):
    credentials = CustomHyperlinkedIdentityField(view_name='credentialsroute-list',
                                                 lookup_field=None)
    aws_creds = serializers.SerializerMethodField()
    openstack_creds = serializers.SerializerMethodField()

    def get_aws_creds(self, obj):
        """
        Include a URL for listing this bucket's contents
        """
        try:
            creds = obj.userprofile.credentials.filter(
                awscredentials__isnull=False).select_subclasses()
            return AWSCredsSerializer(instance=creds, many=True,
                                      context=self.context).data
        except models.UserProfile.DoesNotExist:
            return ""

    def get_openstack_creds(self, obj):
        """
        Include a URL for listing this bucket's contents
        """
        try:
            creds = obj.userprofile.credentials.filter(
                openstackcredentials__isnull=False).select_subclasses()
            return OpenstackCredsSerializer(instance=creds, many=True,
                                            context=self.context).data
        except models.UserProfile.DoesNotExist:
            return ""

    class Meta(UserDetailsSerializer.Meta):
        fields = UserDetailsSerializer.Meta.fields + \
            ('aws_creds', 'openstack_creds', 'credentials')
