from rest_auth.serializers import UserDetailsSerializer
from rest_framework import relations
from rest_framework import serializers

from baselaunch import models
from baselaunch import util
from baselaunch import view_helpers


class CustomHyperlinkedRelatedField(relations.HyperlinkedRelatedField):
    """
    This custom hyperlink field builds up the arguments required to link to a
    nested view of arbitrary depth, provided the ``parent_url_kwargs`` parameter
    is passed in. This parameter must contain a list of ``kwarg`` names that are
    required for django's ``reverse()`` to work. The values for each argument
    are obtained from the serializer context. It's modelled after drf-nested-
    routers' ``NestedHyperlinkedRelatedField``.
    """
    lookup_field = 'pk'

    def __init__(self, *args, **kwargs):
        self.parent_url_kwargs = kwargs.pop('parent_url_kwargs', [])
        super(CustomHyperlinkedRelatedField, self).__init__(*args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.
        May raise a ``NoReverseMatch`` if the ``view_name`` and ``lookup_field``
        attributes are not configured to correctly match the URL conf.
        """
        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, 'pk') and obj.pk is None:
            return None

        reverse_kwargs = {}
        # Use kwargs from view if available. When using the serializer
        # manually, a view may not be available. If so, the required
        # args must be supplied through the serializer context
        if 'view' in self.context:
            reverse_kwargs = {key: val for key, val in self.context['view'].kwargs.items()
                              if key in self.parent_url_kwargs}
        # Let serializer context values override view kwargs
        reverse_kwargs.update({key: val for key, val in self.context.items()
                               if key in self.parent_url_kwargs})
        lookup_value = util.getattrd(obj, self.lookup_field)
        if lookup_value:
            reverse_kwargs.update({self.lookup_url_kwarg: lookup_value})
        return self.reverse(
            view_name, kwargs=reverse_kwargs, request=request, format=format)


class CustomHyperlinkedIdentityField(CustomHyperlinkedRelatedField):
    """
    A version of the ``CustomHyperlinkedRelatedField`` dedicated to creating
    identity links. It's simply copied from rest framework's
    ``relations.HyperlinkedRelatedField``.
    """
    lookup_field = 'pk'

    def __init__(self, *args, **kwargs):
        kwargs['read_only'] = True
        # The asterisk is a special value that DRF has an interpretation
        # for: It will result in the source being set to the current object.
        # itself. (Usually, the source is a field of the current object being
        # serialized)
        kwargs['source'] = '*'
        super(CustomHyperlinkedIdentityField, self).__init__(*args, **kwargs)


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
    ip_protocol = serializers.CharField()
    from_port = serializers.CharField()
    to_port = serializers.CharField()
    cidr_ip = serializers.CharField()


class SecurityGroupSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='security_group-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    description = serializers.CharField()
    rules = CustomHyperlinkedIdentityField(view_name='security_group_rule-list',
                                           lookup_field='id',
                                           lookup_url_kwarg='security_group_pk',
                                           parent_url_kwargs=['cloud_pk'])


class NetworkSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='network-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    state = serializers.CharField()
    cidr_block = serializers.CharField()
    subnets = CustomHyperlinkedIdentityField(view_name='subnet-list',
                                             lookup_field='id',
                                             lookup_url_kwarg='network_pk',
                                             parent_url_kwargs=['cloud_pk'])


class SubnetSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='subnet-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk',
                                                            'network_pk'])
    name = serializers.CharField()
    cidr_block = serializers.CharField()
    network_id = serializers.CharField()


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


class VolumeSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='volume-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    state = serializers.CharField()


class SnapshotSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='snapshot-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    state = serializers.CharField()


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
    image_id = serializers.CharField()
    image_id_url = CustomHyperlinkedIdentityField(view_name='machine_image-detail',
                                                  lookup_field='image_id',
                                                  lookup_url_kwarg='pk',
                                                  parent_url_kwargs=['cloud_pk'])

    placement_zone = ZoneSerializer()

    def __init__(self, *args, **kwargs):
        super(InstanceSerializer, self).__init__(*args, **kwargs)
        # Grabbing instance type for OpenStack is slow because for each
        # instance, an additional request is made to retrieve the actual
        # instance type and this takes ages. Hence, display instance_type only
        # in detail view.
        if isinstance(self.instance, list):
            self.fields.pop('instance_type')
            self.fields.pop('instance_type_url')
        else:
            # For the detail view, do not include the url field
            self.fields.pop('url')


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
    regions = CustomHyperlinkedIdentityField(view_name='region-list',
                                             lookup_field='slug',
                                             lookup_url_kwarg='cloud_pk')
    machine_images = CustomHyperlinkedIdentityField(view_name='machine_image-list',
                                                    lookup_field='slug',
                                                    lookup_url_kwarg='cloud_pk')
    keypairs = CustomHyperlinkedIdentityField(view_name='keypair-list',
                                              lookup_field='slug',
                                              lookup_url_kwarg='cloud_pk')
    security_groups = CustomHyperlinkedIdentityField(view_name='security_group-list',
                                                     lookup_field='slug',
                                                     lookup_url_kwarg='cloud_pk')
    networks = CustomHyperlinkedIdentityField(view_name='network-list',
                                              lookup_field='slug',
                                              lookup_url_kwarg='cloud_pk')
    instance_types = CustomHyperlinkedIdentityField(view_name='instance_type-list',
                                                    lookup_field='slug',
                                                    lookup_url_kwarg='cloud_pk')
    instances = CustomHyperlinkedIdentityField(view_name='instance-list',
                                               lookup_field='slug',
                                               lookup_url_kwarg='cloud_pk')
    volumes = CustomHyperlinkedIdentityField(view_name='volume-list',
                                             lookup_field='slug',
                                             lookup_url_kwarg='cloud_pk')
    snapshots = CustomHyperlinkedIdentityField(view_name='snapshot-list',
                                               lookup_field='slug',
                                               lookup_url_kwarg='cloud_pk')
    buckets = CustomHyperlinkedIdentityField(view_name='bucket-list',
                                             lookup_field='slug',
                                             lookup_url_kwarg='cloud_pk')

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
