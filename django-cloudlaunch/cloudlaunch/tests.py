import json
from unittest.mock import patch
import uuid

from celery.result import AsyncResult
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase
from djcloudbridge import models as cb_models
from djcloudbridge import serializers as cb_serializers
from rest_framework import status
from rest_framework.test import APITestCase

from . import tasks
from .models import (Application,
                     ApplicationDeployment,
                     ApplicationVersion,
                     ApplicationVersionCloudConfig,
                     ApplicationDeploymentTask,
                     CloudImage)


# Create your tests here.
class MockedCeleryTaskCall:
    """Mock a call to a celery task."""

    def __init__(self, task, *args, **kwargs):
        """Specify task, as string, and expected arguments to be passed."""
        self.task = task
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.patcher = patch(self.task)
        self.mocked_task = self.patcher.start()
        celery_id = str(uuid.uuid4())
        return_value = AsyncResult(celery_id)
        self.mocked_task.return_value = return_value
        return return_value

    def __exit__(self, *exc):
        self.patcher.stop()
        self.mocked_task.assert_called_with(
            *self.args, **self.kwargs)
        return False


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

    def _create_cloud(self):
        return cb_models.AWS.objects.create(
            name='Amazon US East 1 - N. Virginia',
            kind='cloud',
        )

    def _create_credentials(self, target_cloud):
        user_profile = cb_models.UserProfile.objects.create(user=self.user)
        return cb_models.AWSCredentials.objects.create(
            cloud=target_cloud,
            access_key='access_key',
            secret_key='secret_key',
            user_profile=user_profile,
            default=True,
        )

    def _create_image(self, target_cloud):
        return CloudImage.objects.create(
            image_id='abc123',
            cloud=target_cloud,
        )

    @patch("cloudlaunch.tasks.launch_appliance.delay")
    def test_create_deployment(self, launch_appliance_task):
        """Create deployment from 'application' and 'application_version'."""
        application_version = self._create_application_version()
        target_cloud = self._create_cloud()
        ubuntu_image = self._create_image(target_cloud)
        credentials = self._create_credentials(target_cloud)
        app_version_cloud_config = \
            ApplicationVersionCloudConfig.objects.create(
                application_version=application_version,
                cloud=target_cloud,
                image=ubuntu_image,
            )
        celery_id = str(uuid.uuid4())
        launch_appliance_task.return_value = AsyncResult(celery_id)
        url = reverse('deployments-list')
        response = self.client.post(url, {
            'name': 'test-deployment',
            'application': application_version.application.slug,
            'application_version': '16.04',
            'target_cloud': target_cloud.slug,
        })
        self.assertEqual(response.status_code, 201)
        launch_appliance_task.assert_called_with(
            'test-deployment',
            app_version_cloud_config.id,
            credentials.as_dict(),
            {},
            None
        )
        app_deployment = ApplicationDeployment.objects.get()
        launch_task = ApplicationDeploymentTask.objects.get(
                action=ApplicationDeploymentTask.LAUNCH,
                deployment=app_deployment, celery_id=celery_id)
        self.assertIsNotNone(launch_task)

    @patch("cloudlaunch.tasks.launch_appliance.delay")
    def test_merging_app_config(self, launch_appliance_task):
        """Specify app_config and verify it is merged correctly."""
        application_version = self._create_application_version()
        target_cloud = self._create_cloud()
        ubuntu_image = self._create_image(target_cloud)
        credentials = self._create_credentials(target_cloud)
        default_launch_config = {
            'foo': 1,
            'bar': 2,
        }
        app_config = {
            'bar': 3,
            'baz': 4,
            'config_cloudlaunch': {
                'instance_user_data': "userdata"
            }
        }
        app_version_cloud_config = \
            ApplicationVersionCloudConfig.objects.create(
                application_version=application_version,
                cloud=target_cloud,
                image=ubuntu_image,
                default_launch_config=json.dumps(default_launch_config)
            )
        celery_id = str(uuid.uuid4())
        launch_appliance_task.return_value = AsyncResult(celery_id)
        url = reverse('deployments-list')
        response = self.client.post(url, {
            'name': 'test-deployment',
            'application': application_version.application.slug,
            'application_version': '16.04',
            'target_cloud': target_cloud.slug,
            'config_app': json.dumps(app_config),
        })
        self.assertEqual(response.status_code, 201)
        launch_appliance_task.assert_called_with(
            'test-deployment',
            app_version_cloud_config.id,
            credentials.as_dict(),
            {
                'foo': 1,  # default from default_launch_config
                'bar': 3,  # config_app overrides default_launch_config
                'baz': 4,  # added by config_app
                'config_cloudlaunch': {
                    'instance_user_data': "userdata"
                }
            },
            'userdata'
        )
        app_deployment = ApplicationDeployment.objects.get()
        launch_task = ApplicationDeploymentTask.objects.get(
                action=ApplicationDeploymentTask.LAUNCH,
                deployment=app_deployment, celery_id=celery_id)
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
        target_cloud = cb_models.AWS.objects.create(
            name='Amazon US East 1 - N. Virginia',
            kind='cloud',
        )
        user_profile = cb_models.UserProfile.objects.create(user=user)
        credentials = cb_models.AWSCredentials.objects.create(
            cloud=target_cloud,
            access_key='access_key',
            secret_key='secret_key',
            user_profile=user_profile,
        )
        app_deployment = ApplicationDeployment.objects.create(
            owner=user,
            name=self.DEPLOYMENT_NAME,
            application_version=application_version,
            target_cloud=target_cloud,
            credentials=credentials
        )
        return app_deployment

    def setUp(self):
        super().setUp()
        self.app_deployment = self._create_test_deployment(user=self.user)

    def test_create_health_check_task(self):
        """Test creating a HEALTH_CHECK type task."""
        with MockedCeleryTaskCall(
                "cloudlaunch.tasks.health_check.delay",
                self.app_deployment.id,
                self.app_deployment.credentials.as_dict()) as async_result:

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
        with MockedCeleryTaskCall(
                "cloudlaunch.tasks.restart_appliance.delay",
                self.app_deployment.id,
                self.app_deployment.credentials.as_dict()) as async_result:

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
        with MockedCeleryTaskCall(
                "cloudlaunch.tasks.delete_appliance.delay",
                self.app_deployment.id,
                self.app_deployment.credentials.as_dict()) as async_result:

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
