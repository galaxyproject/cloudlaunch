from celery.result import AsyncResult
from django.conf import settings
from django.db import models
from django.template.defaultfilters import slugify
import rest_framework.authtoken.models as drf_models

from djcloudbridge import models as cb_models

from polymorphic.models import PolymorphicModel

from smart_selects.db_fields import ChainedForeignKey

import json
import jsonmerge
import djcloudbridge


class Image(cb_models.DateNameAwareModel):
    image_id = models.CharField(max_length=50, verbose_name="Image ID")
    description = models.CharField(max_length=255, blank=True, null=True)
    region = models.ForeignKey(cb_models.Region, on_delete=models.CASCADE,
                               null=False)

    # Cannot be unique together because Azure images are global, not regional
    # class Meta:
    #     unique_together = (("region", "image_id"),)

    def __str__(self):
        return "{0} (on {1})".format(self.name, self.region)


class DeploymentTarget(PolymorphicModel):

    class Meta:
        verbose_name = "Deployment Target"
        verbose_name_plural = "Deployment Targets"

    def __str__(self):
        return "{0}: {1}".format(self._meta.verbose_name, self.id)


class HostDeploymentTarget(DeploymentTarget):

    class Meta:
        verbose_name = "Host"
        verbose_name_plural = "Hosts"


class KubernetesDeploymentTarget(DeploymentTarget):
    kube_config = models.CharField(
        max_length=1024 * 16, blank=False, null=False)

    class Meta:
        verbose_name = "Kubernetes Cluster"
        verbose_name_plural = "Kubernetes Clusters"


class CloudDeploymentTarget(DeploymentTarget):
    target_zone = models.ForeignKey(
        cb_models.Zone, on_delete=models.CASCADE, null=False)

    class Meta:
        unique_together = (("deploymenttarget_ptr", "target_zone"),)
        verbose_name = "Cloud"
        verbose_name_plural = "Clouds"

    def __str__(self):
        return "{0}: {1}".format(self._meta.verbose_name, self.target_zone)


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
    default_launch_config = models.TextField(
        max_length=1024 * 16, blank=True, null=True,
        help_text="Application-wide initial configuration data to parameterize"
                  " the launch with.")
    default_version = models.ForeignKey(
        'ApplicationVersion', on_delete=models.SET_NULL, related_name='+',
        blank=True, null=True)
    display_order = models.IntegerField(blank=False, null=False,
                                        default="10000")

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
                raise Exception("Invalid JSON syntax. Launch config must be in"
                                "JSON format. Cause: {0}".format(e))
        if self.default_version and not self.versions.filter(
                application=self, version=self.default_version).exists():
            raise Exception("The default application version must be a version"
                            " belonging to this application")

        super(Application, self).save(*args, **kwargs)


class ApplicationVersion(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="versions")
    version = models.CharField(max_length=30)
    frontend_component_path = models.CharField(max_length=255, blank=True,
                                               null=True)
    frontend_component_name = models.CharField(max_length=255, blank=True,
                                               null=True)
    backend_component_name = models.CharField(max_length=255, blank=True,
                                              null=True)
    # Userdata max length is 16KB
    default_launch_config = models.TextField(
        max_length=1024 * 16, blank=True, null=True,
        help_text="Version specific configuration data to parameterize the"
                  " launch with.")
    default_target = models.ForeignKey(
        DeploymentTarget, blank=True, null=True, on_delete=models.SET_NULL,
        related_name='+')

    def save(self, *args, **kwargs):
        # validate user data
        if self.default_launch_config:
            try:
                json.loads(self.default_launch_config)
            except Exception as e:
                raise Exception("Invalid JSON syntax. Launch config must be"
                                " in JSON format. Cause: {0}".format(e))
        if self.default_cloud and not self.app_version_config.filter(
                application_version=self, cloud=self.default_cloud).exists():
            raise Exception("The default cloud must be a cloud that this"
                            " version of the application is supported on.")

        return super(ApplicationVersion, self).save()

    def __str__(self):
        return "{0}".format(self.version)

    class Meta:
        unique_together = (("application", "version"),)


class ApplicationVersionTargetConfig(PolymorphicModel):
    application_version = models.ForeignKey(
        ApplicationVersion, on_delete=models.CASCADE,
        related_name="app_version_config")
    target = models.ForeignKey(DeploymentTarget, on_delete=models.CASCADE,
                               related_name="app_version_config")
    # Userdata max length is 16KB
    default_launch_config = models.TextField(
        max_length=1024 * 16, blank=True, null=True,
        help_text="Target specific initial configuration data to parameterize"
                  " the launch with.")

    class Meta:
        unique_together = (("application_version", "target"),)

    def save(self, *args, **kwargs):
        # validate user data
        if self.default_launch_config:
            try:
                json.loads(self.default_launch_config)
            except Exception as e:
                raise Exception("Invalid JSON syntax. Launch config must be "
                                "in JSON format. Cause: {0}".format(e))
        return super(ApplicationVersionTargetConfig, self).save()

    def compute_merged_config(self):
        default_appwide_config = json.loads(
            self.application_version.application.default_launch_config or "{}")
        default_version_config = json.loads(
            self.application_version.default_launch_config or "{}")
        default_cloud_config = json.loads(
            self.default_launch_config or "{}")
        default_combined_config = jsonmerge.merge(
            default_appwide_config, default_version_config)
        return jsonmerge.merge(default_combined_config, default_cloud_config)

    def to_dict(self):
        """
        Serialize the supplied model to a dict.

        A subset of the the model fields is returned as used by current
        plugins but more fields can be serialized as needed.

        @rtype: ``dict``
        @return: A serialized version of the supplied model.
        """
        return {
            'id': self.id,
            'default_launch_config': self.default_launch_config,
            'target': self.target.pk,
            'application_version': self.application_version.pk
        }


class ApplicationVersionCloudConfig(ApplicationVersionTargetConfig):
    image = ChainedForeignKey(Image, chained_field="target",
                              chained_model_field="target__zone__region")

    def to_dict(self):
        return {
            **super(ApplicationVersionCloudConfig, self).to_dict(),
            **{'image_id': self.image.image_id}
        }


class ApplicationDeployment(cb_models.DateNameAwareModel):
    """Application deployment details."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              null=False)
    archived = models.BooleanField(blank=True, default=False)
    application_version = models.ForeignKey(
        ApplicationVersion, on_delete=models.CASCADE, null=False)
    deployment_target = models.ForeignKey(
        DeploymentTarget, on_delete=models.CASCADE, null=False)
    credentials = models.ForeignKey(
        cb_models.Credentials, on_delete=models.CASCADE,
        related_name="target_creds", null=True)
    application_config = models.TextField(
        max_length=1024 * 16, help_text="Application configuration data used "
        "for this launch.", blank=True, null=True)


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
    deployment = models.ForeignKey(
        ApplicationDeployment, on_delete=models.CASCADE, null=False,
        related_name="tasks")
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
                    "Duplicate LAUNCH action for deployment %s"
                    % self.deployment.name)
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

        In the process, we have several data types to deal with. Some task
        results return a ``dict`` while others a ``bool``. In addition, result
        returned from the task broker is returned as a native ``dict`` while,
        after migration, the result for the same task is stored in the database
        as a ``str``. This method tries to standardize on the value returned
        for a given task and, at the very least, always returns a ``dict``.
        More specifically, Celery task results are returned in native format as
        returned from the broker. For the result stored in the database, an
        attempt it made to de-serialize the value from JSON. If that does not
        work, the raw value is returned. It is hence desirable to serialize
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
        else:  # This is an older task which has been migrated so return DB val
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
        See http://docs.celeryproject.org/en/latest/reference/celery.result
        .html#celery.result.AsyncResult.status
        """
        try:
            if self.celery_id:
                task = AsyncResult(self.celery_id)
                return task.backend.get_task_meta(task.id).get('status')
            else:  # An older task which has been migrated so return DB val
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
    # automatically add timestamps when object is created
    added = models.DateTimeField(auto_now_add=True)
    app_version_target_config = models.ForeignKey(
        ApplicationVersionTargetConfig, on_delete=models.CASCADE,
        related_name="+", null=False)
    app_deployment = models.ForeignKey(
        ApplicationDeployment, on_delete=models.SET_NULL, related_name="+",
        null=True)
    app_config = models.TextField(max_length=1024 * 16, blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False)

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
    user_profile = models.ForeignKey(
        djcloudbridge.models.UserProfile, models.CASCADE,
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


# Based on: https://consideratecode.com/2016/10/06/multiple-authentication-toke
# ns-per-user-with-django-rest-framework/
# TODO: Consider using knox if this PR is merged:
# https://github.com/Tivix/django-rest-auth/pull/307
class AuthToken(drf_models.Token):
    # key is no longer primary key, but still indexed and unique
    key = models.CharField("Key", max_length=40, db_index=True, unique=True)
    # relation to user is a ForeignKey, so each user can have more than one
    # token
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='auth_tokens',
        on_delete=models.CASCADE, verbose_name="User"
    )
    name = models.CharField("Name", max_length=64)

    class Meta:
        unique_together = (('user', 'name'),)
