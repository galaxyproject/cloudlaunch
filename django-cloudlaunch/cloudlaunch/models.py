from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.defaultfilters import slugify
import rest_framework.authtoken.models as drf_models

from djcloudbridge import models as cb_models

from smart_selects.db_fields import ChainedForeignKey

import json
import jsonmerge
import djcloudbridge


class Image(cb_models.DateNameAwareModel):
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
    cloud = models.ForeignKey(cb_models.Cloud, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "{0} (on {1})".format(self.name, self.cloud.name)


class AppCategory(models.Model):
    """Categories an app can be associated with."""

    FEATURED = 'FEATURED'
    GALAXY = 'GALAXY'
    SCALABLE = 'SCALABLE'
    VM = 'VM'
    CATEGORY_CHOICES = (
        (FEATURED, 'Featured'),
        (GALAXY, 'Galaxy'),
        (SCALABLE, 'Scalable'),
        (VM, 'Virtual machine')
    )
    name = models.CharField(max_length=100, blank=True, null=True,
                            choices=CATEGORY_CHOICES, unique=True)

    def __str__(self):
        return "{0}".format(self.get_name_display())

    class Meta:
        verbose_name_plural = "App categories"


class Application(cb_models.DateNameAwareModel):

    DEV = 'DEV'
    CERTIFICATION = 'CERTIFICATION'
    LIVE = 'LIVE'
    STATUS_CHOICES = (
        (DEV, 'Development'),
        (CERTIFICATION, 'Certification'),
        (LIVE, 'Live')
    )

    slug = models.SlugField(max_length=100, primary_key=True)
    status = models.CharField(max_length=50, blank=True, null=True,
                              choices=STATUS_CHOICES, default=DEV)
    category = models.ManyToManyField(AppCategory, blank=True)
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
    default_version = models.ForeignKey('ApplicationVersion', on_delete=models.SET_NULL,
                                        related_name='+', blank=True, null=True)
    display_order = models.IntegerField(blank=False, null=False, default="10000")

    def __str__(self):
        return "{0} [{1}]".format(self.name, self.get_status_display())

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


class ApplicationVersion(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=30)
    frontend_component_path = models.CharField(max_length=255, blank=True, null=True)
    frontend_component_name = models.CharField(max_length=255, blank=True, null=True)
    backend_component_name = models.CharField(max_length=255, blank=True, null=True)
    # Userdata max length is 16KB
    default_launch_config = models.TextField(max_length=1024 * 16, help_text="Version "
                                   "specific configuration data to parameterize the launch with.",
                                   blank=True, null=True)
    default_cloud = models.ForeignKey(cb_models.Cloud, on_delete=models.SET_NULL, related_name='+',
                                      blank=True, null=True)

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
    application_version = models.ForeignKey(ApplicationVersion, on_delete=models.CASCADE, related_name="app_version_config")
    cloud = models.ForeignKey(cb_models.Cloud, on_delete=models.CASCADE, related_name="app_version_config")
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


class ApplicationDeployment(cb_models.DateNameAwareModel):
    """Application deployment details."""

    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    archived = models.BooleanField(blank=True, default=False)
    application_version = models.ForeignKey(ApplicationVersion, on_delete=models.CASCADE, null=False)
    target_cloud = models.ForeignKey(cb_models.Cloud, on_delete=models.CASCADE, null=False)
    provider_settings = models.TextField(
        max_length=1024 * 16, help_text="Cloud provider specific settings "
        "used for this launch.", blank=True, null=True)
    application_config = models.TextField(
        max_length=1024 * 16, help_text="Application configuration data used "
        "for this launch.", blank=True, null=True)
    credentials = models.ForeignKey(cb_models.Credentials, on_delete=models.CASCADE, related_name="deployment_creds", null=True)


class ApplicationDeploymentTask(models.Model):
    """Details about a task performing an action for an app deployment."""

    LAUNCH = 'LAUNCH'
    HEALTH_CHECK = 'HEALTH_CHECK'
    RESTART = 'RESTART'
    DELETE = 'DELETE'
    ACTION_CHOICES = (
        (LAUNCH, 'Launch'),
        (HEALTH_CHECK, 'Health check'),
        (RESTART, 'Restart'),
        (DELETE, 'Delete')
    )

    added = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    deployment = models.ForeignKey(ApplicationDeployment, on_delete=models.CASCADE,
                                   null=False, related_name="tasks")
    celery_id = models.TextField(
        max_length=64, help_text="Celery task id for any background jobs "
        "running on this deployment", blank=True, null=True, unique=True)
    action = models.CharField(max_length=255, blank=True, null=True,
                              choices=ACTION_CHOICES)
    _result = models.TextField(
        max_length=1024 * 16, help_text="Result of Celery task", blank=True,
        null=True, db_column='result')
    _status = models.CharField(max_length=64, blank=True, null=True,
                               db_column='status')
    traceback = models.TextField(
        max_length=1024 * 16, help_text="Celery task traceback, if any",
        blank=True, null=True)

    def __str__(self):
        return "{0}".format(self.id)

    def save(self, *args, **kwargs):
        # Check new records and validate at most one LAUNCH task per deployment
        if not self.id and self.action == self.LAUNCH:
            if ApplicationDeploymentTask.objects.filter(
                    deployment=self.deployment,
                    action=self.LAUNCH):
                raise ValueError(
                    "Duplicate LAUNCH action for deployment %s" % self.deployment.name)
        return super(ApplicationDeploymentTask, self).save(*args, **kwargs)

    @property
    def result(self):
        """
        Result can come from a Celery task or the database so we check both.

        While a task is active or up to (by default) one hour after a task
        was initiated, ``result`` field is available from the task. At the
        end of the period, the Celery task is deleted and the data is migrated
        to this table. By wrapping this field as a property, we ensure proper
        data is returned.

        In the process, we have data types to deal with. Some task results
        return a ``dict`` while others a ``bool``. In addition, result
        returned from the task broker is returned as a native ``dict`` while,
        after migration, the result for the same task is stored in the database
        as a ``str``. This method tries to standardize on the value returned
        for a given task and, at the very least, always returns a ``dict``.
        More specifically, Celery task results are returned in native format as
        returned from the broker. For the result stored in the database, an
        attempt it made to de-serialize the value from JSON. If that does not
        work, raw value is returned. It is hence desirable to serialize
        the result value before saving it here.
        """
        r = None
        if self.celery_id:
            try:
                task = AsyncResult(self.celery_id)
                r = task.result
                if task.state == 'FAILURE':
                    return {'exc_message': str(r)}
                if not isinstance(r, dict):
                    r = str(r)
            except Exception as exc:
                return {'exc_message': str(exc)}
        else:  # This is an older task whose task ID has been removed so return DB value
            try:
                r = json.loads(self._result)
            except (ValueError, TypeError):
                r = self._result
        # Always return a dict
        if not isinstance(r, dict):
            return {'result': r}
        else:
            return r

    @result.setter
    def result(self, value):
        """
        Save the result value.

        .. seealso:: result property getter
        """
        self._result = value

    @property
    def status(self):
        """
        Status can come from a Celery task or the database so check both.

        While a task is active or up to (by default) one hour after a task
        was initiated, ``result`` field is available from the task. At the
        end of the period, the Celery task is deleted and the data is migrated
        to this table. By wrapping this field as a property, we ensure proper
        data is returned.

        Available status values include: PENDING, STARTED, RETRY, FAILURE,
        SUCCESS, and "UNKNOWN - `Exception value`".
        See http://docs.celeryproject.org/en/latest/reference/celery.result.html#celery.result.AsyncResult.status
        """
        try:
            if self.celery_id:
                task = AsyncResult(self.celery_id)
                return task.backend.get_task_meta(task.id).get('status')
            else:  # This is an older task whose task ID has been removed so return DB value
                return self._status
        except Exception as exc:
            return 'UNKNOWN - %s' % exc

    @status.setter
    def status(self, value):
        self._status = value


class Usage(models.Model):
    """
    Keep some usage information about instances that are being launched.
    """
    #automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    app_version_cloud_config = models.ForeignKey(ApplicationVersionCloudConfig, on_delete=models.CASCADE,
                                                 related_name="app_version_cloud_config", null=False)
    app_deployment = models.ForeignKey(ApplicationDeployment, on_delete=models.SET_NULL,
                                       related_name="app_version_cloud_config",
                                       null=True)
    app_config =  models.TextField(max_length=1024 * 16, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ['added']
        verbose_name_plural = 'Usage'


class PublicKey(cb_models.DateNameAwareModel):
    """Allow users to store their ssh public keys."""

    public_key = models.TextField(max_length=16384)
    default = models.BooleanField(
        help_text="If set, use as the default public key",
        blank=True, default=False)
    # Ideally, we would auto-generate the fingerprint from the public key
    # instead of prompting the user for it but AWS at least uses two different
    # methods of generating it, making the autogeneration impractical:
    # http://bit.ly/2EIs0kR
    fingerprint = models.CharField(max_length=100, blank=True, null=True)
    user_profile = models.ForeignKey(djcloudbridge.models.UserProfile, models.CASCADE,
                                     related_name='public_key')

    def save(self, *args, **kwargs):
        # Ensure only 1 public key is selected as the 'default'
        # This is not atomic but don't know how to enforce it at the
        # DB level directly.
        if self.default is True:
            previous_default = PublicKey.objects.filter(
                default=True, user_profile=self.user_profile).first()
            if previous_default:
                previous_default.default = False
                previous_default.save()
        return super(PublicKey, self).save()


class UserProfile(models.Model):
    """User profile specific to CloudLaunch."""

    # Link UserProfile to a User model instance
    user = models.OneToOneField(
        User, models.CASCADE, related_name="cloudlaunch_user_profile")

    def __str__(self):
        """Set default display for objects."""
        return "{0} ({1} {2})".format(self.user.username, self.user.first_name,
                                      self.user.last_name)


# Based on: https://consideratecode.com/2016/10/06/multiple-authentication-toke
# ns-per-user-with-django-rest-framework/
class AuthToken(drf_models.Token):
    # key is no longer primary key, but still indexed and unique
    key = models.CharField("Key", max_length=40, db_index=True, unique=True)
    # relation to user is a ForeignKey, so each user can have more than one token
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='auth_tokens',
        on_delete=models.CASCADE, verbose_name="User"
    )
    name = models.CharField("Name", max_length=64)

    class Meta:
        unique_together = (('user', 'name'),)
