from django.contrib.auth.models import User
from django.db import models
from django.template.defaultfilters import slugify
from fernet_fields import EncryptedCharField
from model_utils.managers import InheritanceManager
from smart_selects.db_fields import ChainedForeignKey 


class DateNameAwareModel(models.Model):
    # Automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    # Automatically add timestamps when object is updated
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=60)

    class Meta:
        abstract = True

    def __str__(self):
        return "{0}".format(self.name)


class Cloud(DateNameAwareModel):
    # Ideally, this would be a proxy class so it can be used to uniformly
    # retrieve all cloud objects (e.g., Cloud.objects.all()) but without
    # explicitly existing in the database. However, without a parent class
    # (e.g., Infrastructure), this cannot be due to Django restrictions
    # https://docs.djangoproject.com/en/1.9/topics/db/
    #   models/#base-class-restrictions
    objects = InheritanceManager()
    kind = models.CharField(max_length=10, default='cloud', editable=False)
    slug = models.SlugField(max_length=50, primary_key=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Newly created object, so set slug
            self.slug = slugify(self.name)
        super(Cloud, self).save(*args, **kwargs)


class AWS(Cloud):
    compute = models.ForeignKey('EC2', blank=True, null=True)
    object_store = models.ForeignKey('S3', blank=True, null=True)

    class Meta:
        verbose_name = "AWS"
        verbose_name_plural = "AWS"


class EC2(DateNameAwareModel):
    ec2_region_name = models.CharField(max_length=100,
                                       verbose_name="EC2 region name")
    ec2_region_endpoint = models.CharField(
        max_length=255, verbose_name="EC2 region endpoint")
    ec2_conn_path = models.CharField(max_length=255, default='/',
                                     verbose_name="EC2 conn path")
    ec2_is_secure = models.BooleanField(default=True,
                                        verbose_name="EC2 is secure")
    ec2_port = models.IntegerField(blank=True, null=True,
                                   verbose_name="EC2 port")

    class Meta:
        verbose_name = "EC2"
        verbose_name_plural = "EC2"


class S3(DateNameAwareModel):
    s3_host = models.CharField(max_length=255, blank=True, null=True)
    s3_conn_path = models.CharField(max_length=255, default='/', blank=True,
                                    null=True)
    s3_is_secure = models.BooleanField(default=True)
    s3_port = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "S3"


class OpenStack(Cloud):
    auth_url = models.CharField(max_length=255)
    region_name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "OpenStack"
        verbose_name_plural = "OpenStack"


class Image(DateNameAwareModel):
    """
    A base Image model used by a virtual appliance.

    Applications will use Images and the same application may be available
    on multiple infrastructures so we need this base class so a single
    application field can be used to retrieve all images across
    infrastructures.
    """
    image_id = models.CharField(max_length=50, verbose_name="Image ID")
    description = models.CharField(max_length=255, blank=True, null=True)


class CloudImage(Image):
    cloud = models.ForeignKey(Cloud, blank=True, null=True)

    def __str__(self):
        return "{0} (on {1})".format(self.name, self.cloud.name)


class Application(DateNameAwareModel):
    slug = models.SlugField(max_length=100, primary_key=True)
    # summary is the size of a tweet. description can be of arbitrary length
    summary = models.TextField(max_length=140, blank=True, null=True)
    maintainer = models.TextField(max_length=2048, blank=True, null=True)
    description = models.TextField(max_length=32767, blank=True, null=True)
    info_url = models.URLField(max_length=2048, blank=True, null=True)
    icon_url = models.URLField(max_length=2048, blank=True, null=True)

    def __str__(self):
        return "{0}".format(self.name)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Newly created object, so set slug
            self.slug = slugify(self.name)
        super(Application, self).save(*args, **kwargs)


class ApplicationVersion(models.Model):
    application = models.ForeignKey(Application, related_name="versions")
    version = models.CharField(max_length=30)
    frontend_component_path = models.TextField(max_length=2048, blank=True, null=True)
    frontend_component_name = models.TextField(max_length=2048, blank=True, null=True)
    backend_component_name = models.TextField(max_length=2048, blank=True, null=True)


class ApplicationVersionCloudConfig(models.Model):
    application_version = models.ForeignKey(ApplicationVersion, related_name="app_version_config")
    cloud = models.ForeignKey(Cloud, related_name="app_version_config")
    image = ChainedForeignKey(CloudImage, chained_field="cloud", chained_model_field="cloud")
    default_instance_type = models.CharField(max_length=256, blank=True, null=True)
    # Userdata max length is 16KB
    default_launch_config = models.TextField(max_length=1024 * 16, help_text="Instance "
                                   "Initial configuration data to parameterize the launch.",
                                   blank=True, null=True)
    class Meta:
        unique_together = (("application_version", "cloud"),)

class Credentials(DateNameAwareModel):
    default = models.BooleanField(
        help_text="If set, use as default credentials for the selected cloud",
        blank=True)
    cloud = models.ForeignKey('Cloud', related_name='credentials')
    objects = InheritanceManager()
    user_profile = models.ForeignKey('UserProfile', related_name='credentials')

    def save(self, *args, **kwargs):
        # Ensure only 1 set of credentials is selected as the 'default' for
        # the current cloud.
        # This is not atomic but don't know how to enforce it at the
        # DB level directly.
        if self.default is True:
            previous_default = Credentials.objects.filter(
                cloud=self.cloud, default=True).select_subclasses().first()
            if previous_default:
                previous_default.default = False
                previous_default.save()
        return super(Credentials, self).save()


class AWSCredentials(Credentials):
    access_key = models.CharField(max_length=50)
    secret_key = EncryptedCharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "AWS Credentials"
        verbose_name_plural = "AWS Credentials"

    def as_dict(self):
        return {'aws_access_key': self.access_key,
                'aws_secret_key': self.secret_key,
                }


class OpenStackCredentials(Credentials):
    username = models.CharField(max_length=50)
    password = EncryptedCharField(max_length=50, blank=True, null=True)
    tenant_name = models.CharField(max_length=50, blank=True, null=True)
    project_name = models.CharField(max_length=50, blank=True, null=True)
    project_domain_name = models.CharField(max_length=50, blank=True, null=True)
    user_domain_name = models.CharField(max_length=50, blank=True, null=True)
    identity_api_version = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "OpenStack Credentials"
        verbose_name_plural = "OpenStack Credentials"

    def as_dict(self):
        d = {'os_username': self.username, 'os_password': self.password}
        if self.tenant_name:
            d['os_tenant_name'] = self.tenant_name
        if self.project_name:
            d['os_project_name'] = self.project_name
        if self.project_domain_name:
            d['os_project_domain_name'] = self.project_domain_name
        if self.user_domain_name:
            d['os_user_domain_name'] = self.user_domain_name
        if self.identity_api_version:
            d['os_identity_api_version'] = self.identity_api_version
        return d


class UserProfile(models.Model):
    # Link UserProfile to a User model instance
    user = models.OneToOneField(User)
    slug = models.SlugField(unique=True, primary_key=True, editable=False)

    def __str__(self):
        return "{0} ({1} {2})".format(self.user.username, self.user.first_name,
                                      self.user.last_name)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.user.username)
        super(UserProfile, self).save(*args, **kwargs)
