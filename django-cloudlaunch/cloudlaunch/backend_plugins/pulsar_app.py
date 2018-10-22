import secrets

from cloudlaunch.configurers import AnsibleAppConfigurer

from .base_vm_app import BaseVMAppPlugin


class PulsarAppPlugin(BaseVMAppPlugin):

    def deploy(self, name, task, app_config, provider_config):
        token = secrets.token_urlsafe()
        if not app_config.get('config_pulsar'):
            app_config['config_pulsar'] = {}
        app_config['config_pulsar']['auth_token'] = token
        result = super(PulsarAppPlugin, self).deploy(
            name, task, app_config, provider_config)
        result['pulsar'] = {
            'api_url': 'http://{0}:8913'.format(result['cloudLaunch']['publicIP']),
            'auth_token': token}
        return result

    def _get_configurer(self, app_config):
        return PulsarAnsibleAppConfigurer()


class PulsarAnsibleAppConfigurer(AnsibleAppConfigurer):
    """Add Pulsar specific vars to playbook."""

    def configure(self, app_config, provider_config):
        playbook_vars = [
            ('pulsar_image', app_config.get('config_pulsar', {}).get(
                'pulsar_image', 'galaxy/pulsar:dev')),
            ('pulsar_port', app_config.get('config_pulsar', {}).get(
                'pulsar_port', '8913')),
            ('pulsar_token', app_config['config_pulsar']['auth_token'])
        ]
        return super().configure(app_config, provider_config,
                                 playbook_vars=playbook_vars)
