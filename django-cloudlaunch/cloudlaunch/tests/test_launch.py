from unittest.mock import patch
import yaml

from django.contrib.auth.models import User
from django.urls import reverse
from djcloudbridge import models as cb_models
from rest_framework.test import APILiveServerTestCase

from cloudlaunch.models import (
    Application,
    ApplicationDeployment,
    ApplicationVersion,
    ApplicationVersionCloudConfig,
    ApplicationDeploymentTask,
    CloudDeploymentTarget,
    Image)


class CLLaunchTestBase(APILiveServerTestCase):

    def setUp(self):
        self.user = User.objects.create(username='test-user')
        self.client.force_authenticate(user=self.user)

        def create_mock_provider(self, name, config):
            provider_class = self.get_provider_class("mock")
            return provider_class(config)

        patcher2 = patch('cloudbridge.factory.CloudProviderFactory.create_provider',
                         new=create_mock_provider)
        patcher2.start()
        self.addCleanup(patcher2.stop)

        patcher3 = patch('cloudlaunch.configurers.SSHBasedConfigurer._check_ssh')
        patcher3.start()
        self.addCleanup(patcher3.stop)

        patcher4 = patch('cloudlaunch.configurers.AnsibleAppConfigurer.configure')
        patcher4.start()
        self.addCleanup(patcher4.stop)

        # Patch some background celery tasks to reduce noise in the logs.
        # They don't really affect the tests
        patcher_update_task = patch('cloudlaunch.tasks.update_status_task')
        patcher_update_task.start()
        self.addCleanup(patcher_update_task.stop)
        patcher_migrate_task = patch('cloudlaunch.tasks.migrate_launch_task')
        patcher_migrate_task.start()
        self.addCleanup(patcher_migrate_task.stop)
        patcher_migrate_result = patch('cloudlaunch.tasks.migrate_task_result')
        patcher_migrate_result.start()
        self.addCleanup(patcher_migrate_result.stop)

        super().setUp()

    def assertResponse(self, response, status=None, data_contains=None):
        if status:
            self.assertEqual(response.status_code, status)
        if data_contains:
            self.assertDictContains(response.data, data_contains)

    def assertDictContains(self, dict1, dict2):
        for key in dict2:
            self.assertTrue(key in dict1)
            if isinstance(dict2[key], dict):
                self.assertDictContains(dict1[key], dict2[key])
            else:
                self.assertEqual(dict1[key], dict2[key])


class ApplicationLaunchTests(CLLaunchTestBase):

    DEFAULT_LAUNCH_CONFIG = {
        'foo': 1,
        'bar': 2,
    }
    DEFAULT_APP_CONFIG = {
        'bar': 3,
        'baz': 4,
        'config_cloudlaunch': {
            'instance_user_data': "userdata"
        }
    }

    def _create_application_version(self):
        application = Application.objects.create(
            name="Ubuntu",
            status=Application.LIVE,
        )
        application_version = ApplicationVersion.objects.create(
            application=application,
            version="16.04",
            frontend_component_path="app/marketplace/plugins/plugins.module"
                                    "#PluginsModule",
            frontend_component_name="ubuntu-config",
            backend_component_name="cloudlaunch.backend_plugins.base_vm_app"
                                   ".BaseVMAppPlugin",
        )
        return application_version

    def _create_cloud_region_zone(self):
        cloud = cb_models.AWSCloud.objects.create(
            name='AWS'
        )
        region = cb_models.AWSRegion.objects.create(
            cloud=cloud,
            name='us-east-1'
        )
        zone = cb_models.Zone.objects.create(
            region=region,
            name='us-east-1a'
        )
        return zone

    def _create_credentials(self, target_cloud):
        user_profile = cb_models.UserProfile.objects.get(user=self.user)
        return cb_models.AWSCredentials.objects.create(
            cloud=target_cloud,
            aws_access_key='access_key',
            aws_secret_key='secret_key',
            user_profile=user_profile,
            default=True,
        )

    def _create_image(self, target_region):
        return Image.objects.create(
            image_id='abc123',
            region=target_region,
        )

    def _create_app_version_cloud_config(self,
                                         application_version,
                                         target,
                                         image,
                                         launch_config=DEFAULT_LAUNCH_CONFIG):
        return ApplicationVersionCloudConfig.objects.create(
                application_version=application_version,
                target=target,
                image=image,
                default_launch_config=yaml.safe_dump(launch_config),
            )

    def setUp(self):
        super().setUp()
        # Create test data
        self.application_version = self._create_application_version()
        self.target_zone = self._create_cloud_region_zone()
        self.target_region = self.target_zone.region
        self.target_cloud = self.target_region.cloud
        self.ubuntu_image = self._create_image(self.target_region)
        self.credentials = self._create_credentials(self.target_cloud)
        self.credentials = self._create_credentials(self.target_cloud)
        self.deployment_target = CloudDeploymentTarget.objects.get(
            target_zone=self.target_zone)
        self.app_version_cloud_config = self._create_app_version_cloud_config(
            self.application_version, self.deployment_target, self.ubuntu_image)

    def _create_deployment(self):
        """Create deployment from 'application' and 'application_version'."""
        return self.client.post(reverse('deployments-list'), {
            'name': 'test-deployment',
            'application': self.application_version.application.slug,
            'application_version': self.application_version.version,
            'deployment_target_id': self.deployment_target.id,
        })
        response = self._create_deployment()

    def test_create_deployment(self):
        with patch('cloudbridge.providers.aws.services.AWSInstanceService.delete') as mock_del:
            response = self._create_deployment()
            self.assertResponse(response, status=201, data_contains={
                'name': 'test-deployment',
                'application_version': self.application_version.id,
                'deployment_target': {
                    'id': self.deployment_target.id,
                    'target_zone': {
                        'zone_id': self.target_zone.name
                    }
                },
                'application_config': self.DEFAULT_LAUNCH_CONFIG,
                'app_version_details': {
                    'version': self.application_version.version,
                    'application': {
                        'slug': self.application_version.application.slug,
                    }
                },
            })
            # Check that deployment and its LAUNCH task were created
            app_deployment = ApplicationDeployment.objects.get()
            launch_task = ApplicationDeploymentTask.objects.get(
                action=ApplicationDeploymentTask.LAUNCH,
                deployment=app_deployment)
            self.assertIsNotNone(launch_task)
            mock_del.get.assert_not_called()

    def test_launch_error_triggers_cleanup(self):
        """
        Checks whether an error during launch triggers a cleanup of the instance.
        """
        counter_ref = [0]

        def succeed_on_second_try(count_ref, *args, **kwargs):
            count_ref[0] += 1
            if count_ref[0] > 0 and count_ref[0] < 3:
                raise Exception("Some exception occurred while waiting")

        with patch('cloudbridge.base.resources.BaseInstance.wait_for',
                   side_effect=lambda *args, **kwargs: succeed_on_second_try(
                       counter_ref, *args, **kwargs)) as mock_wait:
            self._create_deployment()
            app_deployment = ApplicationDeployment.objects.get()
            launch_task = ApplicationDeploymentTask.objects.get(
                action=ApplicationDeploymentTask.LAUNCH,
                deployment=app_deployment)
            self.assertNotEquals(launch_task.status, "SUCCESS")
