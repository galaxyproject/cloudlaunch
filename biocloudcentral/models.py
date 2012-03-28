from django.db import models

import biocloudcentral

import logging
log = logging.getLogger(__name__)

class Cloud(models.Model):
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
    ec2_port = models.IntegerField(max_length=6, blank=True, null=True, verbose_name="EC2 port")
    ec2_conn_path = models.CharField(max_length=255, default='/', verbose_name="EC2 conn path")
    cidr_range = models.CharField(max_length=25, blank=True, null=True, verbose_name="CIDR IP range", \
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
    #automatically add timestamps when object is created 
    added = models.DateTimeField(auto_now_add=True) 
    #automatically add timestamps when object is updated
    updated = models.DateTimeField(auto_now=True)
    cloud = models.ForeignKey(Cloud)
    image_id = models.CharField(max_length=30)
    default = models.BooleanField(help_text="Use as the default image for the selected cloud")
    kernel_id = models.CharField(max_length=30, blank=True, null=True)
    ramdisk_id = models.CharField(max_length=30, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s (on %s) %s' % (self.image_id, self.cloud.name, '*DEFAULT*' if self.default else '')
    
    def save(self, *args, **kwargs):
        # Ensure only 1 image is selected as the 'default' for the given cloud
        # This is not atomic but don't know how to enforce it at the DB level directly...
        if self.default is True:
            try:
                previous_default = biocloudcentral.models.Image.objects.get(cloud=self.cloud, default=True)
                previous_default.default = False
                previous_default.save()
            except biocloudcentral.models.Image.DoesNotExist:
                # This is the first entry so no default can exist
                log.debug("Did not find previous default image; set {0} as default".format(self.image_id))
        return super(Image, self).save()
    
    class Meta:
        ordering = ['cloud']
    
