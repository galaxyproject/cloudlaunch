import json
import jsonmerge

from bioblend.cloudman.launch import CloudManLauncher
from cloudbridge.cloud.factory import ProviderList
from rest_framework import serializers

from . import models
from . import tasks
from . import util

from djcloudbridge import models as cb_models
from djcloudbridge import serializers as cb_serializers
from djcloudbridge import view_helpers
from djcloudbridge.drf_helpers import CustomHyperlinkedIdentityField


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
        provider = view_helpers.get_cloud_provider(self.context.get('view'))
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
        model = models.CloudImage
        fields = ('name', 'cloud', 'image_id', 'description')


class StoredJSONField(serializers.JSONField):
    def __init__(self, *args, **kwargs):
        super(StoredJSONField, self).__init__(*args, **kwargs)

    def to_representation(self, value):
        try:
            if value:
                return json.loads(value)
            else:
                return value
        except Exception:
            return value


class AppVersionCloudConfigSerializer(serializers.HyperlinkedModelSerializer):
    cloud = cb_serializers.CloudSerializer(read_only=True)
    image = CloudImageSerializer(read_only=True)
    default_launch_config = serializers.JSONField(source='compute_merged_config')

    class Meta:
        model = models.ApplicationVersionCloudConfig
        fields = ('cloud', 'image', 'default_launch_config', 'default_instance_type')


class AppVersionSerializer(serializers.HyperlinkedModelSerializer):
    cloud_config = AppVersionCloudConfigSerializer(many=True, read_only=True, source='app_version_config')
    default_cloud = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = models.ApplicationVersion
        fields = ('version','cloud_config', 'frontend_component_path', 'frontend_component_name', 'default_cloud')


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
    deployment = serializers.CharField(read_only=True)
    celery_id = serializers.CharField(read_only=True)
    action = serializers.ChoiceField(
        choices=models.ApplicationDeploymentTask.ACTION_CHOICES,
        initial=models.ApplicationDeploymentTask.HEALTH_CHECK)
    status = serializers.CharField(read_only=True)
    result = serializers.DictField(read_only=True)
    traceback = serializers.CharField(read_only=True)

    class Meta:
        model = models.ApplicationDeploymentTask
        exclude = ('deployment', '_result', '_status')

    def create(self, validated_data):
        """
        Fire off a new task for the supplied action.

        Called automatically by the DRF following a POST request.

        :type validated_data: ``dict``
        :param validated_data: Dict containing action the task should perform.
                               Valid actions are `HEALTH_CHECK`, `DELETE`.
        """
        print("deployment task data: %s" % validated_data)
        action = getattr(models.ApplicationDeploymentTask,
                         validated_data.get(
                            'action',
                            models.ApplicationDeploymentTask.HEALTH_CHECK))
        request = self.context.get('view').request
        dpk = self.context['view'].kwargs.get('deployment_pk')
        dpl = models.ApplicationDeployment.objects.get(id=dpk)
        creds = (cb_models.Credentials.objects.get_subclass(
                    id=dpl.credentials.id).as_dict()
                 if dpl.credentials
                 else view_helpers.get_credentials(dpl.target_cloud, request))
        try:
            if action == models.ApplicationDeploymentTask.HEALTH_CHECK:
                async_result = tasks.health_check.delay(dpl.pk, creds)
            elif action == models.ApplicationDeploymentTask.RESTART:
                async_result = tasks.restart_appliance.delay(dpl.pk,
                                                            creds)
            elif action == models.ApplicationDeploymentTask.DELETE:
                async_result = tasks.delete_appliance.delay(dpl.pk,
                                                            creds)
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
    application_config = StoredJSONField(read_only=True)
    # 'application' id is only used when creating a deployment
    application = serializers.CharField(write_only=True, required=False)
    config_app = serializers.JSONField(write_only=True, required=False)
    app_version_details = DeploymentAppVersionSerializer(source="application_version", read_only=True)
    latest_task = serializers.SerializerMethodField()
    launch_task = serializers.SerializerMethodField()
    tasks = CustomHyperlinkedIdentityField(view_name='deployment_task-list',
                                           lookup_field='id',
                                           lookup_url_kwarg='deployment_pk')
    credentials = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = models.ApplicationDeployment
        fields = ('id','name', 'application', 'application_version', 'target_cloud', 'provider_settings',
                  'application_config', 'added', 'updated', 'owner', 'config_app', 'app_version_details',
                  'tasks', 'latest_task', 'launch_task', 'archived', 'credentials')

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
            data['application_version'] = version.id
        return super(DeploymentSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        """
        Create a new ApplicationDeployment object.

        Called automatically by the DRF following a POST request.
        """
        name = validated_data.get("name")
        cloud = validated_data.get("target_cloud")
        version = validated_data.get("application_version")
        cloud_version_config = models.ApplicationVersionCloudConfig.objects.get(
            application_version=version.id, cloud=cloud.slug)
        default_combined_config = cloud_version_config.compute_merged_config()
        request = self.context.get('view').request
        provider = view_helpers.get_cloud_provider(
            self.context.get('view'), cloud_id=cloud.slug)
        credentials = view_helpers.get_credentials(cloud, request)
        try:
            handler = util.import_class(version.backend_component_name)()
            app_config = validated_data.get("config_app", {})

            merged_config = jsonmerge.merge(default_combined_config, app_config)
            cloud_config = util.serialize_cloud_config(cloud_version_config)
            final_ud_config = handler.process_app_config(
                provider, name, cloud_config, merged_config)
            sanitised_app_config = handler.sanitise_app_config(merged_config)
            async_result = tasks.launch_appliance.delay(
                name, cloud_version_config.pk, credentials, merged_config,
                final_ud_config)

            del validated_data['application']
            if 'config_app' in validated_data:
                del validated_data['config_app']
            validated_data['owner_id'] = request.user.id
            validated_data['application_config'] = json.dumps(merged_config)
            validated_data['credentials_id'] = credentials.get('id') or None
            app_deployment = super(DeploymentSerializer, self).create(validated_data)
            self.log_usage(cloud_version_config, app_deployment, sanitised_app_config, request.user)
            models.ApplicationDeploymentTask.objects.create(
                action=models.ApplicationDeploymentTask.LAUNCH,
                deployment=app_deployment, celery_id=async_result.task_id)
            return app_deployment
        except serializers.ValidationError as ve:
            raise ve
        except Exception as e:
            raise serializers.ValidationError({ "error" : str(e) })

    def update(self, instance, validated_data):
        instance.archived = validated_data.get('archived', instance.archived)
        instance.save()
        return instance

    def log_usage(self, app_version_cloud_config, app_deployment, sanitised_app_config, user):
        u = models.Usage(app_version_cloud_config=app_version_cloud_config,
                         app_deployment=app_deployment, app_config=sanitised_app_config, user=user)
        u.save()
