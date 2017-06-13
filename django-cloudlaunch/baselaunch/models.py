from django.contrib.auth.models import User
from django.db import models
from django.template.defaultfilters import slugify
from fernet_fields import EncryptedCharField
from model_utils.managers import InheritanceManager
from smart_selects.db_fields import ChainedForeignKey

# For Public Service
from django_countries.fields import CountryField
import requests
from urllib.parse import urlparse
from django.core.exceptions import ObjectDoesNotExist

import json
import jsonmerge


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
    access_instructions_url = models.URLField(max_length=2048, blank=True, null=True)
    kind = models.CharField(max_length=10, default='cloud', editable=False)
    slug = models.SlugField(max_length=50, primary_key=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Newly created object, so set slug
            self.slug = slugify(self.name)
        super(Cloud, self).save(*args, **kwargs)

    class Meta:
        ordering = ['name']

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
    KEYSTONE_VERSION_CHOICES = (
            ('v2.0', 'v2.0'),
            ('v3.0', 'v3.0')
        )
    auth_url = models.CharField(max_length=255, blank=False, null=False)
    region_name = models.CharField(max_length=100, blank=False, null=False)
    identity_api_version = models.CharField(max_length=10, blank=True, null=True,
                                            choices=KEYSTONE_VERSION_CHOICES)

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
    summary = models.CharField(max_length=140, blank=True, null=True)
    maintainer = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(max_length=32767, blank=True, null=True)
    info_url = models.URLField(max_length=2048, blank=True, null=True)
    icon_url = models.URLField(max_length=2048, blank=True, null=True)
    # Userdata max length is 16KB
    default_launch_config = models.TextField(max_length=1024 * 16, help_text="Application-wide "
                                   "initial configuration data to parameterize the launch with.",
                                   blank=True, null=True)
    default_version = models.ForeignKey('ApplicationVersion', related_name='+',
                                        blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "{0}".format(self.name)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Newly created object, so set slug
            self.slug = slugify(self.name)

        if self.default_launch_config:
            try:
                json.loads(self.default_launch_config)
            except Exception as e:
                raise Exception("Invalid JSON syntax. Launch config must be in JSON format. Cause: {0}".format(e))
        if self.default_version and not self.versions.filter(application=self, version=self.default_version).exists():
            raise Exception("The default application version must be a version belonging to this application")

        super(Application, self).save(*args, **kwargs)

    class Meta:
        ordering = ['name']


class ApplicationVersion(models.Model):
    application = models.ForeignKey(Application, related_name="versions")
    version = models.CharField(max_length=30)
    frontend_component_path = models.CharField(max_length=255, blank=True, null=True)
    frontend_component_name = models.CharField(max_length=255, blank=True, null=True)
    backend_component_name = models.CharField(max_length=255, blank=True, null=True)
    # Userdata max length is 16KB
    default_launch_config = models.TextField(max_length=1024 * 16, help_text="Version "
                                   "specific configuration data to parameterize the launch with.",
                                   blank=True, null=True)
    default_cloud = models.ForeignKey('Cloud', related_name='+', blank=True, null=True,
                                      on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        # validate user data
        if self.default_launch_config:
            try:
                json.loads(self.default_launch_config)
            except Exception as e:
                raise Exception("Invalid JSON syntax. Launch config must be in JSON format. Cause: {0}".format(e))
        if self.default_cloud and not self.app_version_config.filter(application_version=self, cloud=self.default_cloud).exists():
            raise Exception("The default cloud must be a cloud that this version of the application is supported on.")

        return super(ApplicationVersion, self).save()

    def __str__(self):
        return "{0}".format(self.version)

    class Meta:
        unique_together = (("application", "version"),)


class ApplicationVersionCloudConfig(models.Model):
    application_version = models.ForeignKey(ApplicationVersion, related_name="app_version_config")
    cloud = models.ForeignKey(Cloud, related_name="app_version_config")
    image = ChainedForeignKey(CloudImage, chained_field="cloud", chained_model_field="cloud")
    default_instance_type = models.CharField(max_length=256, blank=True, null=True)
    # Userdata max length is 16KB
    default_launch_config = models.TextField(max_length=1024 * 16, help_text="Cloud "
                                   "specific initial configuration data to parameterize the launch with.",
                                   blank=True, null=True)
    class Meta:
        unique_together = (("application_version", "cloud"),)

    def save(self, *args, **kwargs):
        # validate user data
        if self.default_launch_config:
            try:
                json.loads(self.default_launch_config)
            except Exception as e:
                raise Exception("Invalid JSON syntax. Launch config must be in JSON format. Cause: {0}".format(e))
        return super(ApplicationVersionCloudConfig, self).save()

    def compute_merged_config(self):
        default_appwide_config = json.loads(self.application_version.application.default_launch_config or "{}")
        default_version_config = json.loads(self.application_version.default_launch_config or "{}")
        default_cloud_config = json.loads(self.default_launch_config or "{}")
        default_combined_config = jsonmerge.merge(default_appwide_config, default_version_config)
        return jsonmerge.merge(default_combined_config, default_cloud_config)


class ApplicationDeployment(DateNameAwareModel):
    """Application deployment details."""

    owner = models.ForeignKey(User, null=False)
    application_version = models.ForeignKey(ApplicationVersion, null=False)
    target_cloud = models.ForeignKey(Cloud, null=False)
    provider_settings = models.TextField(
        max_length=1024 * 16, help_text="Cloud provider specific settings "
        "used for this launch.", blank=True, null=True)
    application_config = models.TextField(
        max_length=1024 * 16, help_text="Application configuration data used "
        "for this launch.", blank=True, null=True)
    celery_task_id = models.TextField(
        max_length=64, help_text="Celery task id for any background jobs "
        "running on this deployment", blank=True, null=True, unique=True)
    task_result = models.TextField(
        max_length=1024 * 16, help_text="Result of Celery task", blank=True,
        null=True)
    task_status = models.CharField(max_length=64, blank=True, null=True)
    task_traceback = models.TextField(
        max_length=1024 * 16, help_text="Celery task traceback, if any",
        blank=True, null=True)


class Credentials(DateNameAwareModel):
    default = models.BooleanField(
        help_text="If set, use as default credentials for the selected cloud",
        blank=True, default=False)
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
    access_key = models.CharField(max_length=50, blank=False, null=False)
    secret_key = EncryptedCharField(max_length=50, blank=False, null=False)

    class Meta:
        verbose_name = "AWS Credentials"
        verbose_name_plural = "AWS Credentials"

    def as_dict(self):
        return {'aws_access_key': self.access_key,
                'aws_secret_key': self.secret_key,
                }


class OpenStackCredentials(Credentials):
    username = models.CharField(max_length=50, blank=False, null=False)
    password = EncryptedCharField(max_length=50, blank=False, null=False)
    project_name = models.CharField(max_length=50, blank=False, null=False)
    project_domain_name = models.CharField(max_length=50, blank=True, null=True)
    user_domain_name = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "OpenStack Credentials"
        verbose_name_plural = "OpenStack Credentials"

    def as_dict(self):
        d = {'os_username': self.username, 'os_password': self.password}
        if self.project_name:
            d['os_project_name'] = self.project_name
        if self.project_domain_name:
            d['os_project_domain_name'] = self.project_domain_name
        if self.user_domain_name:
            d['os_user_domain_name'] = self.user_domain_name
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

### PublicServer Models ###
class Tag(models.Model):
    """
    Tag referencing a keyword for search features
    """
    name = models.TextField(primary_key=True)


class Sponsor(models.Model):
    """
    A Sponsor is defined by his name and his link url.
    Directly inspired by https://wiki.galaxyproject.org/PublicGalaxyServers Sponsor(s) part
    """
    name = models.TextField()
    url = models.URLField(null=True)

    def __str__(self):
        return "{0}".format(self.name)


class Location(models.Model):
    """
    A location containing the latitude and longitude (fetched from the ip) and
    a django_country https://github.com/SmileyChris/django-countries
    """
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    city = models.TextField(blank=True, null=True)

    country = CountryField(blank='(select country)')

    def __str__(self):
        return "Country: {0}, Latitude: {1}, Longitude: {2}".format(self.country,
                                                                    self.latitude,
                                                                    self.longitude,
                                                                    self.city)


class PublicService(DateNameAwareModel):
    """
    Public Service class to display the public services available,
    for example, on https://wiki.galaxyproject.org/PublicGalaxyServers
    The fields have been inspired by this public galaxy page
    """
    slug = models.SlugField(max_length=100, primary_key=True)
    links = models.URLField()
    location = models.ForeignKey(Location, blank=True, null=True)
    purpose = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    email_user_support = models.EmailField(blank=True, null=True)
    quotas = models.TextField(blank=True, null=True)
    sponsors = models.ManyToManyField(Sponsor, blank=True)
    # Featured links means a more important link to show "first"
    featured = models.BooleanField(default=False)
    # The referenced application, if existing
    application = models.ForeignKey(Application, blank=True, null=True)
    # The url link to the logo of the Service
    logo = models.URLField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return "{0}".format(self.name)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Newly created object, so set slug
            self.slug = slugify(self.name)

        # Construct the API to find geolocation from ip
        api_hostname = 'http://ip-api.com'
        return_format = 'json'
        parsed_url = urlparse(self.links)
        netloc = parsed_url.netloc
        geolocation_api = '{0}/{1}/{2}'.format(api_hostname, return_format, netloc)

        response = requests.get(geolocation_api)
        if  response.status_code != 200:
            raise Exception("Couldn't find the geolocation from ip {0}: {1}".format(geolocation_api, response.status_code))
        # Construct or get the Location
        json_geoloc = response.json()
        self.location = Location.objects.get_or_create(longitude=json_geoloc["lon"],
                                    latitude=json_geoloc["lat"],
                                    defaults={
                                        'country': json_geoloc["countryCode"],
                                        'city': json_geoloc["city"],
                                    },)[0]

        super(PublicService, self).save(*args, **kwargs)


class Usage(models.Model):
    """
    Keep some usage information about instances that are being launched.
    """
    #automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    app_version_cloud_config = models.ForeignKey(ApplicationVersionCloudConfig,
                                                 related_name="app_version_cloud_config", null=False)
    app_deployment = models.ForeignKey(ApplicationDeployment, related_name="app_version_cloud_config",
                                       null=True, on_delete=models.SET_NULL)
    app_config =  models.TextField(max_length=1024 * 16, blank=True, null=True)
    user = models.ForeignKey(User, null=False)

    class Meta:
        ordering = ['added']
        verbose_name_plural = 'Usage'
