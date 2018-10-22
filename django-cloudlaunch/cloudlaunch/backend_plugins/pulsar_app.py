import secrets
import yaml
from .base_vm_app import BaseVMAppPlugin


class PulsarAppPlugin(BaseVMAppPlugin):

    def deploy(self, name, task, app_config, provider_config):
        token = secrets.token_urlsafe()
        user_data = provider_config.get('cloud_user_data')
        provider_config['cloud_user_data'] = user_data.replace("${PULSAR_TOKEN}", token)
        result = super(PulsarAppPlugin, self).deploy(
            name, task, app_config, provider_config)
        result['pulsar'] = {
            'api_url': 'http://{0}:8913'.format(result['cloudLaunch']['publicIP']),
            'auth_token': token}
        return result
