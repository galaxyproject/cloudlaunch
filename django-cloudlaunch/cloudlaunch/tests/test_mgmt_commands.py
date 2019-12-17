from io import StringIO
import os
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from cloudlaunch import models as cl_models


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


class ImportAppCommandTestCase(TestCase):

    APP_DATA_PATH_NEW = os.path.join(
        TEST_DATA_PATH, 'apps_new.yaml')
    APP_DATA_PATH_UPDATED = os.path.join(
        TEST_DATA_PATH, 'apps_update.yaml')
    APP_DATA_PATH_URL = 'https://raw.githubusercontent.com/CloudVE/' \
                        'cloudlaunch-registry/master/app-registry.yaml'

    def test_import_app_data_no_args(self):
        with self.assertRaisesRegex(CommandError,
                                    "-f/--file -u/--url is required"):
            call_command('import_app_data')

    def test_import_new_app_data_from_file(self):
        call_command('import_app_data', '-f', self.APP_DATA_PATH_NEW)
        app_obj = cl_models.Application.objects.get(
            slug='biodocklet')
        self.assertEquals(app_obj.name, 'BioDocklet')
        self.assertIn('bcil/biodocklets:RNAseq_paired',
                      app_obj.default_version.default_launch_config)

    def test_import_existing_app_data_from_file(self):
        call_command('import_app_data', '-f', self.APP_DATA_PATH_NEW)
        call_command('import_app_data', '-f', self.APP_DATA_PATH_UPDATED)
        app_obj = cl_models.Application.objects.get(
            slug='cloudman-20')
        self.assertEquals(app_obj.name, 'CloudMan 2.0 Updated')
        self.assertEquals(app_obj.summary, 'A different summary')
        self.assertIn('some_new_text',
                      app_obj.default_version.default_launch_config)

    def test_import_new_app_data_from_url(self):
        call_command('import_app_data', '--url', self.APP_DATA_PATH_URL)
        app_obj = cl_models.Application.objects.get(
            slug='pulsar-standalone')
        self.assertEquals(app_obj.name, 'Galaxy Cloud Bursting')
        self.assertIn('config_cloudlaunch',
                      app_obj.default_version.default_launch_config)

    def test_export_matches_import(self):
        call_command('import_app_data', '-f', self.APP_DATA_PATH_NEW)
        out = StringIO()
        call_command('export_app_data', stdout=out)
        with open(self.APP_DATA_PATH_NEW) as f:
            self.assertEquals(f.read(), out.getvalue())

    def test_export_subset(self):
        call_command('import_app_data', '-f', self.APP_DATA_PATH_NEW)
        out = StringIO()
        call_command('export_app_data', '-a', 'biodocklet', stdout=out)
        self.assertNotIn('cloudman-20', out.getvalue())
