from django.db import models

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
        ordering = ['cloud']

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
        return u'%s (on %s)' % (self.image_id, self.cloud.region_name)
    
    def save(self, *args, **kwargs):
        # TODO: ensure only 1 image is selected as the 'default' for the given cloud
        return super(Image, self).save()
    
    class Meta:
        ordering = ['cloud']
    
