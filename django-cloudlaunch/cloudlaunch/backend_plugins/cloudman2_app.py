"""CloudMan 2.0 application plugin implementation."""
import json
import random
import string
import base64
from urllib.parse import urljoin

from cloudlaunch.configurers import AnsibleAppConfigurer

from .simple_web_app import SimpleWebAppPlugin


class CloudMan2AppPlugin(SimpleWebAppPlugin):
    """CloudLaunch appliance implementation for CloudMan 2.0."""

    @staticmethod
    def validate_app_config(provider, name, cloud_config, app_config):
        """Format any app-specific configurations."""
        return super(CloudMan2AppPlugin,
                     CloudMan2AppPlugin).validate_app_config(
                         provider, name, cloud_config, app_config)

    @staticmethod
    def sanitise_app_config(app_config):
        """Sanitize any app-specific data that will be stored in the DB."""
        return super(CloudMan2AppPlugin,
                     CloudMan2AppPlugin).sanitise_app_config(app_config)

    def _configure_host(self, name, task, app_config, provider_config):
        result = super()._configure_host(name, task, app_config, provider_config)
        host = provider_config.get('host_address')
        pulsar_token = app_config['config_cloudman2'].get('pulsar_token')
        result['cloudLaunch'] = {'applicationURL':
                                 'https://{0}/'.format(host),
                                 'pulsar_token': pulsar_token}
        task.update_state(
            state='PROGRESSING',
            meta={'action': "Waiting for CloudMan to become available at %s"
                            % result['cloudLaunch']['applicationURL']})
        login_url = urljoin(result['cloudLaunch']['applicationURL'],
                            'cloudman/openid/openid/KeyCloak')
        self.wait_for_http(login_url, ok_status_codes=[302])
        return result

    def _get_configurer(self, app_config):
        # CloudMan2 can only be configured with ansible
        return CloudMan2AnsibleAppConfigurer()


class CloudMan2AnsibleAppConfigurer(AnsibleAppConfigurer):
    """Add CloudMan2 specific vars to playbook."""

    def configure(self, app_config, provider_config):
        host = provider_config.get('host_config').get('host_address')
        # Create a random token for Pulsar if it's set to be used
        token_length = 40  # chars
        token_contents = (string.ascii_lowercase + string.ascii_uppercase +
                          string.digits)
        pulsar_token = ''.join(random.choice(token_contents) for i in range(
            token_length)) if app_config.get(
            'config_cloudman2', {}).get('pulsarOnly') else None
        if pulsar_token:
            app_config['config_cloudman2']['pulsar_token'] = pulsar_token
        # rancher config will be added to cluster_data in the helm chart, once rancher
        # details are available
        cm_initial_cluster_data = {
            'cloud_config': provider_config.get('cloud_config'),
            'host_config': provider_config.get('host_config'),
            'app_config': app_config
        }
        playbook_vars = [
            ('cm_boot_image', app_config.get('config_cloudman2', {}).get(
                'cm_boot_image')),
            ('rancher_server', host),
            ('rancher_pwd', app_config.get('config_cloudman2', {}).get(
                'clusterPassword')),
            ('cm_initial_cluster_data', base64.b64encode(
                json.dumps(cm_initial_cluster_data).encode('utf-8')).decode('utf-8'))
        ]
        return super().configure(app_config, provider_config,
                                 playbook_vars=playbook_vars)
