from django.db import models
from django.template.defaultfilters import slugify


class DateNameAwareModel(models.Model):
    # Automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    # Automatically add timestamps when object is updated
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=60)

    class Meta:
        abstract = True


class Infrastructure(DateNameAwareModel):
    # Indicates what kind of infrastructure a class represents
    KIND = (
        ('cloud', 'clouds'),
        ('container', 'containers'),
        ('local', 'local'),
    )
    kind = models.CharField(max_length=10, choices=KIND, editable=False)

    def __str__(self):
        return self.name


class Cloud(Infrastructure):

    def __init__(self, *args, **kwargs):
        # Set the default value for the `kind` field for this type of
        # infrastructure
        self._meta.get_field('kind').default = 'cloud'
        super(Cloud, self).__init__(*args, **kwargs)

    class Meta:
        proxy = True


class AWSEC2(Cloud):
    region_name = models.CharField(max_length=100)
    region_endpoint = models.CharField(max_length=255)
    is_secure = models.BooleanField()
    ec2_port = models.IntegerField(blank=True, null=True,
                                   verbose_name="EC2 port")
    ec2_conn_path = models.CharField(max_length=255, default='/',
                                     verbose_name="EC2 conn path")

    class Meta:
        verbose_name = "AWS EC2"
        verbose_name_plural = "AWS EC2"


class AWSS3(Cloud):
    s3_host = models.CharField(max_length=255, blank=True, null=True)
    s3_port = models.IntegerField(blank=True, null=True)
    s3_conn_path = models.CharField(max_length=255, default='/', blank=True,
                                    null=True)

    class Meta:
        verbose_name = "AWS S3"
        verbose_name_plural = "AWS S3"


class OpenStack(Cloud):
    auth_url = models.CharField(max_length=255)
    region_name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "OpenStack"
        verbose_name_plural = "OpenStack"


class Image(DateNameAwareModel):
    image_id = models.CharField(max_length=50, verbose_name="Image ID")
    description = models.CharField(max_length=255, blank=True, null=True)
    infrastructure = models.ForeignKey(Infrastructure, blank=True, null=True)

    def __str__(self):
        return "{0} ({1})".format(self.name, self.image_id)


class Application(DateNameAwareModel):
    slug = models.SlugField(max_length=50, primary_key=True)
    description = models.TextField(blank=True, null=True)
    info_url = models.URLField(blank=True, null=True)

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
    # Image provides a link to the infrastructure and is hence a ManyToMany
    # field as the same application definition and version may be available
    # on multiple infrastructures.
    image_id = models.ManyToManyField(Image, blank=True)
    # Userdata max length is 16KB
    launch_data = models.TextField(max_length=1024 * 16, help_text="Instance "
                                   "user data to parameterize the launch.",
                                   blank=True, null=True)
