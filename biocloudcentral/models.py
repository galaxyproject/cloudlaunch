from django.db import models

import biocloudcentral

import yaml
import logging
log = logging.getLogger(__name__)


class Cloud(models.Model):
    """
    Cloud connection properties. These are tailored for use with boto library.
    """
    CLOUD_TYPES = (
        ('ec2', 'AWS EC2'),
        ('openstack', 'OpenStack'),
        ('opennebula', 'OpenNebula'),
        # ('euca', 'Eucalyptus'), # Not yet supported
        # ('nimbus', 'Nimbus'), # Not yet supported
    )
    #automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    #automatically add timestamps when object is updated
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=100)
    cloud_type = models.CharField(max_length=30, choices=CLOUD_TYPES)
    bucket_default = models.CharField(max_length=255, blank=True, null=True)
    region_name = models.CharField(max_length=100)
    region_endpoint = models.CharField(max_length=255)
    ec2_port = models.IntegerField(max_length=6, blank=True, null=True,
        verbose_name="EC2 port")
    ec2_conn_path = models.CharField(max_length=255, default='/',
        verbose_name="EC2 conn path")
    cidr_range = models.CharField(max_length=25, blank=True, null=True,
        verbose_name="CIDR IP range",
        help_text="Available IP range for all instances in this cloud in CIDR format")
    is_secure = models.BooleanField()
    s3_host = models.CharField(max_length=255)
    s3_port = models.IntegerField(max_length=6, blank=True, null=True)
    s3_conn_path = models.CharField(max_length=255, default='/')

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.get_cloud_type_display())

    class Meta:
        ordering = ['cloud_type']


class InstanceType(models.Model):
    """
    Instance type properties. Each instance is linked to a cloud and available
    instances need to be defined for each cloud.
    """
    #automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    #automatically add timestamps when object is updated
    updated = models.DateTimeField(auto_now=True)
    cloud = models.ForeignKey(Cloud)
    pretty_name = models.CharField(max_length=100)
    tech_name = models.CharField(max_length=100)
    description = models.CharField(max_length=100)

    def __unicode__(self):
        return u'%s' % (self.pretty_name)

    class Meta:
        ordering = ['cloud', '-updated']


class Image(models.Model):
    """
    Machine image properties for a cloud. Available images need to be defined
    for each cloud.
    """
    #automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    #automatically add timestamps when object is updated
    updated = models.DateTimeField(auto_now=True)
    cloud = models.ForeignKey(Cloud)
    image_id = models.CharField(max_length=30)
    description = models.CharField(max_length=255)
    default = models.BooleanField(help_text="Use as the default image for the selected cloud")
    kernel_id = models.CharField(max_length=30, blank=True, null=True)
    ramdisk_id = models.CharField(max_length=30, blank=True, null=True)

    def __unicode__(self):
        return (u'[%s] %s (%s) %s' %
            (self.cloud.name, self.description, self.image_id,
            '*DEFAULT*' if self.default else ''))

    def save(self, *args, **kwargs):
        # Ensure only 1 image is selected as the 'default' for the given cloud
        # This is not atomic but don't know how to enforce it at the DB level directly...
        if self.default is True:
            try:
                previous_default = biocloudcentral.models.Image.objects.get(
                    cloud=self.cloud, default=True)
                previous_default.default = False
                previous_default.save()
            except biocloudcentral.models.Image.DoesNotExist:
                # This is the first entry so no default can exist
                log.debug("Did not find previous default image; set {0} as default"
                    .format(self.image_id))
        return super(Image, self).save()

    class Meta:
        ordering = ['cloud']


class Flavor(models.Model):
    """
    A Flavour is a specific configuration of pre-defined, extra user-data to be
    passed as parameters during a launch.
    Can be used to set different cloudman/launch configurations.
    """
    #automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    #automatically add timestamps when object is updated
    updated = models.DateTimeField(auto_now=True)
    image = models.ForeignKey(Image)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    user_data = models.CharField(max_length=1024 * 16) # userdata max length is 16KB
    default = models.BooleanField(help_text="Use as the default flavor for the selected cloud")

    def __unicode__(self):
        return (u'[%s] %s %s' %
            (self.image.image_id, self.name,
            '*DEFAULT*' if self.default else ''))

    def save(self, *args, **kwargs):
        # validate user data
        if self.user_data:
            try:
                yaml.load(self.user_data)
            except Exception, e:
                raise Exception("Invalid yaml syntax. User data must be in yaml format. Cause: {0}".format(e))
        # Ensure only 1 flavour is selected as the 'default' for the given cloud
        # This is not atomic but don't know how to enforce it at the DB level directly...
        if self.default is True:
            try:
                previous_default = biocloudcentral.models.Flavor.objects.get(image=self.image, default=True)
                previous_default.default = False
                previous_default.save()
            except biocloudcentral.models.Flavor.DoesNotExist:
                # This is the first entry so no default can exist
                log.debug("Did not find previous default Flavor; set {0} as default"
                    .format(self.pk))
        return super(Flavor, self).save()

    class Meta:
        ordering = ['image']

class DataBucket(models.Model):
    """
    Keep info about available object store bucket.

    Not currently used.
    """
    #automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    #automatically add timestamps when object is updated
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=63)  # S3 buckets can be between 3 and 63 characters long
    public = models.BooleanField(default=True)
    description = models.CharField(max_length=255)
    cloud = models.ForeignKey(Cloud)  # Allow use of other object stores as well

    def __unicode__(self):
        return u'{0}'.format(self.name)

    class Meta:
        ordering = ['cloud', 'name']


class Usage(models.Model):
    """
    Keep some usage information about instances that are being launched.
    """
    #automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    #automatically add timestamps when object is updated
    updated = models.DateTimeField(auto_now=True)
    cloud_name = models.CharField(max_length=100)
    cloud_type = models.CharField(max_length=30)
    image_id = models.CharField(max_length=30)
    instance_type = models.CharField(max_length=100)
    cluster_type = models.CharField(max_length=30, blank=True, null=True)
    storage_type = models.CharField(max_length=30, blank=True, null=True)
    storage_size = models.IntegerField(blank=True, null=True)
    user_id = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)

    def __unicode__(self):
        return u'{pk} | {add} | {name} | {iid} | {itype} | {ctype} ' \
                '| {stype} | {user} | {email}'\
                .format(pk=self.pk, add=self.added, name=self.cloud_name,
                        cltype=self.cluster_type, stype=self.storage_type,
                        iid=self.image_id, itype=self.instance_type,
                        user=self.user_id, email=self.email)

    class Meta:
        ordering = ['updated', 'cloud_type']
        verbose_name_plural = 'Usage'
