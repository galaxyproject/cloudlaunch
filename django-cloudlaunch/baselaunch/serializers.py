from rest_auth.serializers import UserDetailsSerializer
from rest_framework import relations
from rest_framework import serializers
from rest_framework.reverse import reverse

from baselaunch import models


class CustomHyperlinkedRelatedField(relations.HyperlinkedRelatedField):
    """
    This custom hyperlink field  builds up the arguments required
    to link to a nested view of arbitrary depth, provided the
    'parent_url_kwargs' parameter is passed in. This parameter must contain
    a list of kwarg names that are required for django's reverse() to work. The
    values for each argument are obtained from the serializer context.
    It's modelled after drf-nested-routers' NestedHyperlinkedRelatedField
    """
    lookup_field = 'pk'

    def __init__(self, *args, **kwargs):
        self.parent_url_kwargs = kwargs.pop('parent_url_kwargs', [])
        super(CustomHyperlinkedRelatedField, self).__init__(*args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.
        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, 'pk') and obj.pk is None:
            return None

        lookup_value = self.lookup_value(obj, self.lookup_field)
        if not lookup_value:
            # if no pk value was found, return an empty url
            return ""
        reverse_kwargs = {arg: self.context[arg]
                          for arg in self.parent_url_kwargs}
        reverse_kwargs.update({self.lookup_url_kwarg: lookup_value})
        return self.reverse(
            view_name, kwargs=reverse_kwargs, request=request, format=format)

    def lookup_value(self, obj, field_name):
        """
        Returns an attribute value in a given object. The field_name may be
        nested, in which case the operation will be applied repeatedly to
        get the innermost value.
        e.g. lookup_value(my_obj, "region.name")
        """
        current_obj = obj
        for attr in field_name.split("."):
            current_obj = getattr(current_obj, attr)
        return current_obj


class CustomHyperlinkedIdentityField(CustomHyperlinkedRelatedField):
    """
    A version of the CustomHyperlinkedRelatedField dedicated to creating
    identity links. It's simply copied from rest framework's
    relations.HyperlinkedRelatedField
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

    def __init__(self, *args, **kwargs):
        super(RegionSerializer, self).__init__(*args, **kwargs)
        # For the detail view, do not include the url field
        if not self.context.get('list', False):
            self.fields.pop('url')


class MachineImageSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='machine_image-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    description = serializers.CharField()

    def __init__(self, *args, **kwargs):
        super(MachineImageSerializer, self).__init__(*args, **kwargs)
        # For the detail view, do not include the url field
        if not self.context.get('list', False):
            self.fields.pop('url')


class KeyPairSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='keypair-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    material = serializers.CharField()

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

    def __init__(self, *args, **kwargs):
        super(SecurityGroupSerializer, self).__init__(*args, **kwargs)
        # For the detail view, do not include the url field
        if not self.context.get('list', False):
            self.fields.pop('url')


class NetworkSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
#     url = CustomHyperlinkedIdentityField(view_name='network-detail',
#                                          lookup_field='id',
#                                          lookup_url_kwarg='pk',
#                                          parent_url_kwargs=['cloud_pk'])
    name = serializers.CharField()
    state = serializers.CharField()
    cidr_block = serializers.CharField()
    subnets = CustomHyperlinkedIdentityField(view_name='subnet-list',
                                             lookup_field='id',
                                             lookup_url_kwarg='network_pk',
                                             parent_url_kwargs=['cloud_pk'])


class SubnetSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    cidr_block = serializers.CharField()


class InstanceTypeSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = CustomHyperlinkedIdentityField(view_name='instance_type-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
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
        if self.context.get('list', False):
            self.fields.pop('instance_type')
            self.fields.pop('instance_type_url')
        else:
            # For the detail view, do not include the url field
            self.fields.pop('url')


class BucketSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    contents = CustomHyperlinkedIdentityField(view_name='object-list',
                                              lookup_field='id',
                                              lookup_url_kwarg='bucket_pk',
                                              parent_url_kwargs=['cloud_pk'])


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
