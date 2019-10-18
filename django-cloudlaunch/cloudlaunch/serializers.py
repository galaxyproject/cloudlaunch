import logging
import yaml

import jsonmerge

from bioblend.cloudman.launch import CloudManLauncher

from cloudbridge.factory import ProviderList

from rest_framework import serializers

from rest_polymorphic.serializers import PolymorphicSerializer

from djcloudbridge import models as cb_models
from djcloudbridge import serializers as cb_serializers
from djcloudbridge import view_helpers as cb_view_helpers
from djcloudbridge.drf_helpers import CustomHyperlinkedIdentityField

from . import models
from . import tasks
from . import util

log = logging.getLogger(__name__)


class CloudManSerializer(serializers.Serializer):
    """
    Handle CloudMan application requests.

    Note that this serializer (and the endpoint) are temporary until the
    new CloudMan is developed that natively supports multiple clouds.
    """

    saved_clusters = serializers.SerializerMethodField()

    def get_saved_clusters(self, obj):
        """
        Fetch a list of saved CloudMan clusters from AWS.

        This only fetches saved clusters that used AWS since it appears that
        was the only place this feature was actively used.
        """
        provider = cb_view_helpers.get_cloud_provider(self.context.get('view'))
        if provider.PROVIDER_ID != ProviderList.AWS:
            return []
        # Since we're only working with the AWS, there's no need to specify
        # the cloud argument as it defaults to AWS in BioBlend.
        cml = CloudManLauncher(provider.session_cfg.get('aws_access_key_id'),
                               provider.session_cfg.get('aws_secret_access_key'),
                               None)
        return cml.get_clusters_pd().get('clusters', [])


class CloudImageSerializer(serializers.HyperlinkedModelSerializer):
    cloud = serializers.HyperlinkedRelatedField(
        view_name='djcloudbridge:cloud-detail', many=False, read_only=True)

    class Meta:
        model = models.Image
        fields = ('name', 'cloud', 'image_id', 'description')


class StoredYAMLField(serializers.JSONField):
    def __init__(self, *args, **kwargs):
        super(StoredYAMLField, self).__init__(*args, **kwargs)

    def to_representation(self, value):
        try:
            if value:
                return yaml.safe_load(value)
            else:
                return value
        except Exception:
            return value


class DeploymentTargetSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.DeploymentTarget
        exclude = ('polymorphic_ctype',)


class DeploymentZoneSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    zone_id = serializers.CharField(read_only=True)
    region = cb_serializers.CloudRegionListSerializer(read_only=True)
    cloud = cb_serializers.CloudPolymorphicSerializer(read_only=True, source="region.cloud")

    class Meta:
        model = cb_models.Zone
        fields = ('cloud', 'region', 'zone_id', 'name')


class CloudDeploymentTargetSerializer(DeploymentTargetSerializer):
    target_zone = DeploymentZoneSerializer()

    class Meta(DeploymentTargetSerializer.Meta):
        model = models.CloudDeploymentTarget


class DeploymentTargetPolymorphicSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        models.CloudDeploymentTarget: CloudDeploymentTargetSerializer,
        models.HostDeploymentTarget: DeploymentTargetSerializer,
        models.KubernetesDeploymentTarget: DeploymentTargetSerializer,
    }


class AppVersionTargetConfigSerializer(serializers.HyperlinkedModelSerializer):
    target = DeploymentTargetPolymorphicSerializer(read_only=True)
    default_launch_config = serializers.JSONField(source='compute_merged_config')

    class Meta:
        model = models.ApplicationVersionTargetConfig
        fields = ('target', 'default_launch_config')


class AppVersionCloudConfigSerializer(AppVersionTargetConfigSerializer):
    image = CloudImageSerializer(read_only=True)

    class Meta(AppVersionTargetConfigSerializer.Meta):
        model = models.ApplicationVersionCloudConfig
        fields = ('target', 'image', 'default_launch_config')


class AppVersionCloudConfigPolymorphicSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        models.ApplicationVersionCloudConfig: AppVersionCloudConfigSerializer,
    }


class AppVersionSerializer(serializers.HyperlinkedModelSerializer):
    target_config = AppVersionCloudConfigPolymorphicSerializer(
        many=True, read_only=True, source='app_version_config')
    default_target = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = models.ApplicationVersion
        fields = ('version', 'target_config', 'frontend_component_path', 'frontend_component_name', 'default_target')


class ApplicationSerializer(serializers.HyperlinkedModelSerializer):
    slug = serializers.CharField(read_only=True)
    versions = AppVersionSerializer(many=True, read_only=True)
    default_version = serializers.SlugRelatedField(read_only=True, slug_field='version')

    class Meta:
        model = models.Application
        exclude = ('default_launch_config', 'category')


class DeploymentAppSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(read_only=True)

    class Meta:
        model = models.Application
        fields = ('slug', 'name')


class DeploymentAppVersionSerializer(serializers.ModelSerializer):
    application = DeploymentAppSerializer(read_only=True)

    class Meta:
        model = models.ApplicationVersion
        fields = ('version', 'frontend_component_path', 'frontend_component_name', 'application')


class DeploymentTaskSerializer(serializers.ModelSerializer):
    url = CustomHyperlinkedIdentityField(view_name='deployment_task-detail',
                                         lookup_field='id',
                                         lookup_url_kwarg='pk',
                                         parent_url_kwargs=['deployment_pk',
                                                            'deployment_task_pk'])
    celery_id = serializers.CharField(read_only=True)
    action = serializers.ChoiceField(
        choices=models.ApplicationDeploymentTask.ACTION_CHOICES,
        initial=models.ApplicationDeploymentTask.HEALTH_CHECK)
    status = serializers.CharField(read_only=True)
    result = serializers.DictField(read_only=True)
    traceback = serializers.CharField(read_only=True)

    class Meta:
        model = models.ApplicationDeploymentTask
        exclude = ('_result', '_status')
        read_only_fields = ('deployment',)

    @staticmethod
    def _resolve_credentials(deployment, request):
        if deployment.credentials:
            return deployment.credentials
        elif isinstance(deployment, models.CloudDeploymentTarget):
            return cb_view_helpers.get_credentials(
                deployment.deployment_target.target_zone.region.cloud, request)
        else:
            return None

    def create(self, validated_data):
        """
        Fire off a new task for the supplied action.

        Called automatically by the DRF following a POST request.

        :type validated_data: ``dict``
        :param validated_data: Dict containing action the task should perform.
                               Valid actions are `HEALTH_CHECK`, `DELETE`.
        """
        log.debug("Deployment task data: %s", validated_data)
        action = getattr(models.ApplicationDeploymentTask,
                         validated_data.get(
                             'action',
                             models.ApplicationDeploymentTask.HEALTH_CHECK))
        request = self.context.get('view').request
        dpk = self.context['view'].kwargs.get('deployment_pk')
        dpl = models.ApplicationDeployment.objects.get(id=dpk)
        creds = self._resolve_credentials(dpl, request)
        cred_dict = creds.to_dict() if creds else {}
        try:
            if action == models.ApplicationDeploymentTask.HEALTH_CHECK:
                async_result = tasks.health_check.delay(dpl.id, cred_dict)
            elif action == models.ApplicationDeploymentTask.RESTART:
                async_result = tasks.restart_appliance.delay(dpl.id, cred_dict)
            elif action == models.ApplicationDeploymentTask.DELETE:
                async_result = tasks.delete_appliance.delay(dpl.id, cred_dict)
            return models.ApplicationDeploymentTask.objects.create(
                action=action, deployment=dpl, celery_id=async_result.task_id)
        except serializers.ValidationError as ve:
            raise ve
        except Exception as e:
            raise serializers.ValidationError({"error": str(e)})

    def validate_action(self, value):
        """Make sure only one LAUNCH task exists per deployment."""
        if value == models.ApplicationDeploymentTask.LAUNCH:
            dpk = self.context['view'].kwargs.get('deployment_pk')
            dpl = models.ApplicationDeployment.objects.get(id=dpk)
            if models.ApplicationDeploymentTask.objects.filter(
                    deployment=dpl,
                    action=models.ApplicationDeploymentTask.LAUNCH):
                raise serializers.ValidationError(
                    "Duplicate LAUNCH action for deployment %s" % dpl.name)
        return value.upper()


class DeploymentSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(read_only=True)
    name = serializers.CharField(required=True)
    provider_settings = serializers.CharField(read_only=True)
    application_config = StoredYAMLField(read_only=True)
    # 'application' id is only used when creating a deployment
    application = serializers.CharField(write_only=True, required=False)
    config_app = serializers.JSONField(write_only=True, required=False)
    app_version_details = DeploymentAppVersionSerializer(source="application_version", read_only=True)
    latest_task = serializers.SerializerMethodField()
    launch_task = serializers.SerializerMethodField()
    tasks = CustomHyperlinkedIdentityField(view_name='deployment_task-list',
                                           lookup_field='id',
                                           lookup_url_kwarg='deployment_pk')
    deployment_target = DeploymentTargetPolymorphicSerializer(read_only=True)
    deployment_target_id = serializers.CharField(write_only=True)
    credentials = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = models.ApplicationDeployment
        fields = ('id','name', 'application', 'application_version', 'deployment_target', 'deployment_target_id',
                  'provider_settings', 'application_config', 'added', 'updated', 'owner', 'config_app',
                  'app_version_details', 'tasks', 'latest_task', 'launch_task', 'archived', 'credentials')

    def get_latest_task(self, obj):
        """Provide task info about the most recenly updated deployment task."""
        try:
            task = obj.tasks.latest('updated')
            return DeploymentTaskSerializer(
                task, context={'request': self.context['request'],
                               'deployment_pk': obj.id}).data
        except models.ApplicationDeploymentTask.DoesNotExist:
            return None

    def get_launch_task(self, obj):
        """Provide task info about the most recenly updated deployment task."""
        try:
            task = obj.tasks.filter(action='LAUNCH').first()
            return DeploymentTaskSerializer(
                task, context={'request': self.context['request'],
                               'deployment_pk': obj.id}).data
        except models.ApplicationDeploymentTask.DoesNotExist:
            return None

    def to_internal_value(self, data):
        application = data.get('application')
        version = data.get('application_version')
        if application and version:
            version = models.ApplicationVersion.objects.get(application=application, version=version)
            # data dict is immutable when running tests so copy is needed
            data = data.copy()
            data['application_version'] = version.id
        return super(DeploymentSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        """
        Create a new ApplicationDeployment object.

        Called automatically by the DRF following a POST request.
        """
        log.debug("Creating a new deployment: {0}".format(
            validated_data.get("name")))
        name = validated_data.get("name")
        target = validated_data.get("deployment_target_id")
        version = validated_data.get("application_version")
        target_version_config = models.ApplicationVersionTargetConfig.objects.get(
            application_version=version, target=target)
        default_combined_config = target_version_config.compute_merged_config()
        request = self.context.get('view').request
        # FIXME: The target may not be a cloud, and therefore, the provider should not
        # be instantiated here
        if isinstance(target_version_config, models.ApplicationVersionCloudConfig):
            cloud = target_version_config.target.target_zone.region.cloud
            credentials = cb_view_helpers.get_credentials(cloud, request)
        else:
            # FIXME: For now, we don't handle non-cloud credentials
            credentials = None
        try:
            app_config = validated_data.get("config_app", {})
            merged_app_config = jsonmerge.merge(
                default_combined_config, app_config)
            final_ud_config, sanitised_app_config = self._validate_and_sanitise(
                target_version_config, merged_app_config, name, version)
            async_result = tasks.create_appliance.delay(
                name, target_version_config.pk, credentials, merged_app_config,
                final_ud_config)

            del validated_data['application']
            if 'config_app' in validated_data:
                del validated_data['config_app']
            validated_data['owner_id'] = request.user.id
            validated_data['application_config'] = yaml.safe_dump(
                merged_app_config, default_flow_style=False)
            validated_data['credentials_id'] = credentials.get('id') or None
            app_deployment = super(DeploymentSerializer, self).create(validated_data)
            self.log_usage(target_version_config, app_deployment, sanitised_app_config, request.user)
            models.ApplicationDeploymentTask.objects.create(
                action=models.ApplicationDeploymentTask.LAUNCH,
                deployment=app_deployment, celery_id=async_result.task_id)
            return app_deployment
        except serializers.ValidationError as ve:
            raise ve
        except Exception as e:
            raise serializers.ValidationError(
                {"error": "An exception creating a deployment of %s: %s)" %
                 (version.backend_component_name, e)})

    def _validate_and_sanitise(self, target_version_config, merged_app_config, name, version):
        handler = util.import_class(version.backend_component_name)()

        if isinstance(target_version_config, models.ApplicationVersionCloudConfig):
            zone = target_version_config.target.target_zone
            # FIXME: provider should not be instantiated here, since the target may not
            # be a cloud. In addition, all parameters to external plugins should be
            # simple JSON. Therefore, we should pass in the provider config here, instead
            # of the provider. The plugin will need to instantiate the appropriate provider
            # depending on the type of target.
            provider = cb_view_helpers.get_cloud_provider(
                self.context.get('view'), zone=zone)
            target_config = target_version_config.to_dict()
            final_ud_config = handler.validate_app_config(
                provider, name, target_config, merged_app_config)
            sanitised_app_config = handler.sanitise_app_config(merged_app_config)
            return final_ud_config, sanitised_app_config
        return None, None

    def update(self, instance, validated_data):
        instance.archived = validated_data.get('archived', instance.archived)
        instance.save()
        return instance

    def log_usage(self, target_version_config, app_deployment, sanitised_app_config, user):
        u = models.Usage(app_version_target_config=target_version_config,
                         app_deployment=app_deployment, app_config=sanitised_app_config, user=user)
        u.save()


class PublicKeySerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='public-key-detail', read_only=True)

    class Meta:
        model = models.PublicKey
        exclude = ['user_profile']

    def create(self, validated_data):
        user_profile, _ = models.UserProfile.objects.get_or_create(
            user=self.context.get('view').request.user)
        return models.PublicKey.objects.create(
            user_profile=user_profile, **validated_data)


class AuthTokenSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    key = serializers.CharField(read_only=True)

    class Meta:
        model = models.AuthToken
        fields = ('id', 'name', 'key')

    def create(self, validated_data):
        user = self.context.get('view').request.user
        return models.AuthToken.objects.create(user=user, **validated_data)


############
# Serializers for data sent to Plugins
############

class CloudImagePluginSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Image
        fields = ('name', 'image_id', 'description')


class DeploymentTargetPluginSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.DeploymentTarget
        exclude = ('polymorphic_ctype',)


class BaseCloudPluginSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()

    class Meta:
        model = cb_models.Cloud
        exclude = ('polymorphic_ctype',)


class OpenStackCloudSerializer(BaseCloudPluginSerializer):
    auth_url = serializers.CharField(allow_blank=True)
    identity_api_version = serializers.BooleanField()


class CloudPluginSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        cb_models.Cloud: BaseCloudPluginSerializer,
        cb_models.AWSCloud: BaseCloudPluginSerializer,
        cb_models.AzureCloud: BaseCloudPluginSerializer,
        cb_models.GCPCloud: BaseCloudPluginSerializer,
        cb_models.OpenStackCloud: OpenStackCloudSerializer
    }


class BaseCloudRegionSerializer(serializers.ModelSerializer):
    region_id = serializers.CharField(read_only=True)
    name = serializers.CharField(allow_blank=False)

    class Meta:
        model = cb_models.Region
        exclude = ('polymorphic_ctype',)


class AWSRegionSerializer(BaseCloudRegionSerializer):
    ec2_endpoint_url = serializers.CharField(allow_blank=True)
    ec2_is_secure = serializers.BooleanField()
    ec2_validate_certs = serializers.BooleanField()
    s3_endpoint_url = serializers.CharField(allow_blank=True)
    s3_is_secure = serializers.BooleanField()
    s3_validate_certs = serializers.BooleanField()


class CloudRegionPluginSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        cb_models.Region: BaseCloudRegionSerializer,
        cb_models.AWSRegion: AWSRegionSerializer,
        cb_models.AzureRegion: BaseCloudRegionSerializer,
        cb_models.GCPRegion: BaseCloudRegionSerializer,
        cb_models.OpenStackRegion: BaseCloudRegionSerializer
    }


class DeploymentZonePluginSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    zone_id = serializers.CharField(read_only=True)
    region = CloudRegionPluginSerializer(read_only=True)
    cloud = CloudPluginSerializer(read_only=True, source="region.cloud")

    class Meta:
        model = cb_models.Zone
        fields = ('cloud', 'region', 'zone_id', 'name')


class CloudDeploymentTargetPluginSerializer(DeploymentTargetSerializer):
    target_zone = DeploymentZonePluginSerializer()

    class Meta(DeploymentTargetSerializer.Meta):
        model = models.CloudDeploymentTarget


class DeploymentTargetPluginSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        models.CloudDeploymentTarget: CloudDeploymentTargetPluginSerializer,
        models.HostDeploymentTarget: DeploymentTargetPluginSerializer,
        models.KubernetesDeploymentTarget: DeploymentTargetPluginSerializer,
    }


class TargetConfigPluginSerializer(serializers.ModelSerializer):
    target = DeploymentTargetPluginSerializer()
#    default_launch_config = serializers.JSONField(source='compute_merged_config')

    class Meta:
        model = models.ApplicationVersionTargetConfig
        fields = ('target', 'default_launch_config')


class CloudConfigPluginSerializer(TargetConfigPluginSerializer):
    image = CloudImagePluginSerializer()

    class Meta(AppVersionTargetConfigSerializer.Meta):
        model = models.ApplicationVersionCloudConfig
        fields = ('target', 'image')
