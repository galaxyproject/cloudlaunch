from rest_framework.serializers import ValidationError
from .app_plugin import BaseAppPlugin

class BaseVMAppPlugin(BaseAppPlugin):

    @staticmethod
    def process_app_config(name, cloud_version_config, credentials, app_config):
        return {}

    def launch_app(self, task, name, cloud_version_config, credentials, app_config, user_data):
        result = super(BaseVMAppPlugin, self).launch_app(task, name, cloud_version_config, credentials, app_config, user_data)
        result['cloudLaunch']['applicationURL'] = 'http://{0}'.format(result['cloudLaunch']['publicIP'])
        return result
