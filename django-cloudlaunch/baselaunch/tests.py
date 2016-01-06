from django.core.urlresolvers import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Application


# Create your tests here.
class ApplicationTests(APITestCase):

    APP_DATA = {'name': 'HelloWorldApp',
                'slug': 'helloworldapp',
                'description': 'HelloWorldDesc',
                'info_url': 'http://www.cloudlaunch.org'}

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
