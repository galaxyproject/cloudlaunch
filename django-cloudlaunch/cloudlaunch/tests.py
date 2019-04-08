import json
from contextlib import contextmanager
from unittest.mock import patch
import uuid

from celery.result import AsyncResult
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase
from djcloudbridge import models as cb_models
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (Application,
                     ApplicationDeployment,
                     ApplicationVersion,
                     ApplicationVersionCloudConfig,
                     ApplicationDeploymentTask,
                     CloudDeploymentTarget,
                     Image)


@contextmanager
def mocked_celery_task_call(task, *args, **kwargs):
    patcher = patch(task)
    mocked_task = patcher.start()
    celery_id = str(uuid.uuid4())
    return_value = AsyncResult(celery_id)
    mocked_task.return_value = return_value
    yield return_value
    patcher.stop()
    mocked_task.assert_called_with(*args, **kwargs)


class BaseAPITestCase(APITestCase):
    """Base class for all CloudLaunch API testcases."""
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


class BaseAuthenticatedAPITestCase(BaseAPITestCase):
    """Base class for tests that need an authenticated user."""

    def setUp(self):
        """Create user and log in."""
        self.user = User.objects.create(username='test-user')
        self.client.force_authenticate(user=self.user)


class ApplicationTests(APITestCase):

    APP_DATA = {'name': 'HelloWorldApp',
                'slug': 'helloworldapp',
                'description': 'HelloWorldDesc',
                'info_url': 'http://www.cloudlaunch.org',
                'status': 'LIVE',
                }

    def _create_application(self, app_data):
        url = reverse('application-list')
        return self.client.post(url, app_data, format='json')

    def test_create_application(self):
        """
        Ensure we can create a new application object.
        """
        response = self._create_application(ApplicationTests.APP_DATA)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Application.objects.count(), 1)
        self.assertEqual(Application.objects.get().name, 'HelloWorldApp')
        self.assertEqual(Application.objects.get().slug, 'helloworldapp')

    def test_get_application(self):
        """
        Ensure we can retrieve an application object.
        """
        data = ApplicationTests.APP_DATA
        self._create_application(data)
        url = reverse('application-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(data, response.json()['results'][0])

    def test_delete_application(self):
        """
        Ensure we can delete an application object.
        """
        data = ApplicationTests.APP_DATA
        new_app = self._create_application(data)
        url = reverse('application-detail', args=[new_app.data['slug']])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Application.objects.count(), 0)

    def test_update_application(self):
        """
        Ensure we can update an application object.
        """
        data = ApplicationTests.APP_DATA.copy()
        new_app = self._create_application(data)
        url = reverse('application-detail', args=[new_app.data['slug']])
        data['name'] = 'HelloWorldApp2'
        data['description'] = 'HelloWorldDesc2'
        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Application.objects.get().name, 'HelloWorldApp2')
        self.assertEqual(Application.objects.get().description,
                         'HelloWorldDesc2')


class UserTests(APITestCase):

    LOGIN_DATA = {'username': 'TestUser',
                  'email': 'testuser@cloudlaunch.org',
                  'password': 'test_user_pass'
                  }

    REG_DATA = {'username': 'TestUser',
                'email': 'testuser@cloudlaunch.org',
                'password1': 'test_user_pass',
                'password2': 'test_user_pass'
                }

    def _register_user(self, data):
        url = reverse('rest_auth_reg:rest_register')
        return self.client.post(url, data, format='json')

    def _login_user(self, data):
        url = reverse('rest_auth:rest_login')
        response = self.client.post(url, data, format='json').json()
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + response.get('key'))

    def _register_and_login(self):
        self._register_user(UserTests.REG_DATA)
        self._login_user(UserTests.LOGIN_DATA)

    def test_register_user(self):
        """
        Ensure we can register a new user.
        """
        response = self._register_user(UserTests.REG_DATA)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'TestUser')
        self.assertEqual(User.objects.get().email,
                         'testuser@cloudlaunch.org')
        self.assertIsNotNone(User.objects.get().password)

    def test_get_user(self):
        """
        Ensure we can retrieve a registered user
        """
        self._register_and_login()
        url = reverse('rest_auth:rest_user_details')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        login_sanitized = UserTests.LOGIN_DATA.copy()
        del login_sanitized['password']
        self.assertDictContainsSubset(login_sanitized, response.json())

    def test_update_user(self):
        """
        Ensure we can update a user
        """
        self._register_and_login()
        url = reverse('rest_auth:rest_user_details')
        data = UserTests.REG_DATA.copy()
        data['first_name'] = 'Mr. Test'
        data['last_name'] = 'User'
        response = self.client.put(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.get().first_name, 'Mr. Test')
        self.assertEqual(User.objects.get().last_name, 'User')

    def test_create_cloud_creds(self):
        """
        Ensure we can update a user's stored cloud credentials
        """
        # TODO: Ensure that a user's cloud credentials can be created.
        self._register_and_login()


class ApplicationDeploymentTests(BaseAuthenticatedAPITestCase):

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
            name='default'
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
                default_launch_config=json.dumps(launch_config),
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

    def test_create_deployment(self):
        """Create deployment from 'application' and 'application_version'."""
        with mocked_celery_task_call(
                "cloudlaunch.tasks.create_appliance.delay",
                'test-deployment',
                self.app_version_cloud_config.id,
                self.credentials.to_dict(),
                self.DEFAULT_LAUNCH_CONFIG,
                None) as async_result:

            response = self.client.post(reverse('deployments-list'), {
                'name': 'test-deployment',
                'application': self.application_version.application.slug,
                'application_version': self.application_version.version,
                'deployment_target_id': self.deployment_target.id,
            })
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
                'latest_task': {
                    'celery_id': async_result.id,
                    'action': 'LAUNCH'
                },
                'launch_task': {
                    'celery_id': async_result.id,
                    'action': 'LAUNCH'
                }
            })
        # Check that deployment and its LAUNCH task were created
        app_deployment = ApplicationDeployment.objects.get()
        launch_task = ApplicationDeploymentTask.objects.get(
                action=ApplicationDeploymentTask.LAUNCH,
                deployment=app_deployment)
        self.assertIsNotNone(launch_task)

    def test_merging_app_config(self):
        """Specify app_config and verify it is merged correctly."""
        with mocked_celery_task_call(
                "cloudlaunch.tasks.create_appliance.delay",
                'test-deployment',
                self.app_version_cloud_config.id,
                self.credentials.to_dict(),
                {'foo': 1, 'bar': 3, 'baz': 4,
                 'config_cloudlaunch': {'instance_user_data': "userdata"}},
                'userdata') as async_result:

            response = self.client.post(reverse('deployments-list'), {
                'name': 'test-deployment',
                'application': self.application_version.application.slug,
                'application_version': self.application_version.version,
                'deployment_target_id': self.deployment_target.id,
                'config_app': json.dumps(self.DEFAULT_APP_CONFIG),
            })
            self.assertResponse(response, status=201, data_contains={
                'name': 'test-deployment',
                'application_version': self.application_version.id,
                'deployment_target': {
                    'id': self.deployment_target.id,
                    'target_zone': {
                        'zone_id': self.target_zone.name
                    }
                },
                'application_config': {
                    'foo': 1,  # default from DEFAULT_LAUNCH_CONFIG
                    'bar': 3,  # config_app overrides DEFAULT_LAUNCH_CONFIG
                    'baz': 4,  # added by config_app
                    'config_cloudlaunch': {
                        'instance_user_data': "userdata"
                    }
                },
                'app_version_details': {
                    'version': self.application_version.version,
                    'application': {
                        'slug': self.application_version.application.slug,
                    }
                },
                'latest_task': {
                    'celery_id': async_result.id,
                    'action': 'LAUNCH'
                },
                'launch_task': {
                    'celery_id': async_result.id,
                    'action': 'LAUNCH'
                }
            })
        # Check that deployment and its LAUNCH task were created
        app_deployment = ApplicationDeployment.objects.get()
        launch_task = ApplicationDeploymentTask.objects.get(
                action=ApplicationDeploymentTask.LAUNCH,
                deployment=app_deployment)
        self.assertIsNotNone(launch_task)


class ApplicationDeploymentTaskTests(BaseAuthenticatedAPITestCase):

    DEPLOYMENT_NAME = "test-deployment"

    def _create_test_deployment(self, user):
        application = Application.objects.create(
            name="Ubuntu",
            status=Application.LIVE,
        )
        application_version = ApplicationVersion.objects.create(
            application=application,
            version="1.0",
        )
        target_cloud = cb_models.AWSCloud.objects.create(
            name='AWS'
        )
        target_region = cb_models.AWSRegion.objects.create(
            cloud=target_cloud,
            name='us-east',
        )
        target_zone = cb_models.Zone.objects.create(
            region=target_region,
            name='default',
        )
        user_profile = cb_models.UserProfile.objects.get(user=user)
        credentials = cb_models.AWSCredentials.objects.create(
            cloud=target_cloud,
            aws_access_key='access_key',
            aws_secret_key='secret_key',
            user_profile=user_profile,
        )
        deployment_target = CloudDeploymentTarget.objects.get(target_zone=target_zone)
        app_deployment = ApplicationDeployment.objects.create(
            owner=user,
            name=self.DEPLOYMENT_NAME,
            application_version=application_version,
            deployment_target=deployment_target,
            credentials=credentials
        )
        return app_deployment

    def setUp(self):
        super().setUp()
        self.app_deployment = self._create_test_deployment(user=self.user)

    def test_create_health_check_task(self):
        """Test creating a HEALTH_CHECK type task."""
        with mocked_celery_task_call(
                "cloudlaunch.tasks.health_check.delay",
                self.app_deployment.id,
                self.app_deployment.credentials.to_dict()) as async_result:

            response = self.client.post(
                reverse('deployment_task-list',
                        kwargs={'deployment_pk': self.app_deployment.id}),
                {'action': 'HEALTH_CHECK'})
            self.assertResponse(response, status=201, data_contains={
                'celery_id': async_result.id,
                'action': 'HEALTH_CHECK',
                'deployment': self.app_deployment.id,
            })
        # check that ApplicationDeploymentTask was created, will throw
        # DoesNotExist if missing
        task = ApplicationDeploymentTask.objects.get(action='HEALTH_CHECK',
                                                     celery_id=async_result.id,
                                                     deployment=self.app_deployment)
        self.assertIsNotNone(task)

    def test_create_restart_task(self):
        """Test creating a RESTART type task."""
        with mocked_celery_task_call(
                "cloudlaunch.tasks.restart_appliance.delay",
                self.app_deployment.id,
                self.app_deployment.credentials.to_dict()) as async_result:

            response = self.client.post(
                reverse('deployment_task-list',
                        kwargs={'deployment_pk': self.app_deployment.id}),
                {'action': 'RESTART'})
            self.assertResponse(response, status=201, data_contains={
                'celery_id': async_result.id,
                'action': 'RESTART',
                'deployment': self.app_deployment.id,
            })
        # check that ApplicationDeploymentTask was created, will throw
        # DoesNotExist if missing
        task = ApplicationDeploymentTask.objects.get(action='RESTART',
                                                     celery_id=async_result.id,
                                                     deployment=self.app_deployment)
        self.assertIsNotNone(task)

    def test_create_delete_task(self):
        """Test creating a DELETE type task."""
        with mocked_celery_task_call(
                "cloudlaunch.tasks.delete_appliance.delay",
                self.app_deployment.id,
                self.app_deployment.credentials.to_dict()) as async_result:

            response = self.client.post(
                reverse('deployment_task-list',
                        kwargs={'deployment_pk': self.app_deployment.id}),
                {'action': 'DELETE'})
            self.assertResponse(response, status=201, data_contains={
                'celery_id': async_result.id,
                'action': 'DELETE',
                'deployment': self.app_deployment.id,
            })
        # check that ApplicationDeploymentTask was created, will throw
        # DoesNotExist if missing
        task = ApplicationDeploymentTask.objects.get(action='DELETE',
                                                     celery_id=async_result.id,
                                                     deployment=self.app_deployment)
        self.assertIsNotNone(task)

    def test_only_one_launch_task(self):
        """Test LAUNCH task not allowed if one already exists."""
        # Create LAUNCH task for the test deployment
        ApplicationDeploymentTask.objects.create(
            deployment=self.app_deployment,
            action=ApplicationDeploymentTask.LAUNCH)
        self.assertEqual(
            len(ApplicationDeploymentTask.objects.filter(
                deployment=self.app_deployment,
                action=ApplicationDeploymentTask.LAUNCH)),
            1,
            "Only one LAUNCH task should exist.")
        # Attempt to create a LAUNCH task
        response = self.client.post(
            reverse('deployment_task-list',
                    kwargs={'deployment_pk': self.app_deployment.id}),
            {'action': 'LAUNCH'})
        self.assertResponse(response, status=400, data_contains={
            'action': ['Duplicate LAUNCH action for deployment {}'
                       .format(self.DEPLOYMENT_NAME)]
        })
        # LAUNCH task count is still 1
        self.assertEqual(
            len(ApplicationDeploymentTask.objects.filter(
                deployment=self.app_deployment,
                action=ApplicationDeploymentTask.LAUNCH)),
            1,
            "Only one LAUNCH task should exist.")


class ApplicationDeploymentTaskModelTestCase(TestCase):

    def _create_test_deployment(self):
        user = User.objects.create(username='test-user')
        application = Application.objects.create(
            name="Ubuntu",
            status=Application.LIVE,
        )
        application_version = ApplicationVersion.objects.create(
            application=application,
            version="1.0",
        )
        target_cloud = cb_models.AWSCloud.objects.create(
            name='AWS',
        )
        target_region = cb_models.AWSRegion.objects.create(
            cloud=target_cloud,
            name='us-east',
        )
        target_zone = cb_models.Zone.objects.create(
            region=target_region,
            name='default',
        )
        user_profile = cb_models.UserProfile.objects.get(user=user)
        credentials = cb_models.AWSCredentials.objects.create(
            cloud=target_cloud,
            aws_access_key='access_key',
            aws_secret_key='secret_key',
            user_profile=user_profile,
        )
        deployment_target = CloudDeploymentTarget.objects.get(target_zone=target_zone)
        app_deployment = ApplicationDeployment.objects.create(
            owner=user,
            name='test-deployment',
            application_version=application_version,
            deployment_target=deployment_target,
            credentials=credentials
        )
        return app_deployment

    def setUp(self):
        super().setUp()
        self.app_deployment = self._create_test_deployment()

    def test_only_one_launch_task_allowed(self):
        """Test only one LAUNCH task per deployment at model level."""
        ApplicationDeploymentTask.objects.create(
            deployment=self.app_deployment,
            action=ApplicationDeploymentTask.LAUNCH)
        with self.assertRaises(ValueError, msg="Should have not allowed a "
                                               "second LAUNCH task.") as cm:
            ApplicationDeploymentTask.objects.create(
                deployment=self.app_deployment,
                action=ApplicationDeploymentTask.LAUNCH)
        self.assertEqual(str(cm.exception), "Duplicate LAUNCH action for "
                                            "deployment test-deployment")
