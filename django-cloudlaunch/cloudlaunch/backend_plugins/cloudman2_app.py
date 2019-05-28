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
        host = provider_config.get('host_config', {}).get('host_address')
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


AWS_CLOUD_CONF = \
    "[Global]\n"

AZURE_CLOUD_CONF = \
    "[Global]\n"

GCP_CLOUD_CONF = \
    "[Global]\n"

OPENSTACK_CLOUD_CONF = \
    "[Global]\n" \
    "username=$os_username\n" \
    "password=$os_password\n" \
    "auth-url=$os_auth_url\n" \
    "domain-name=$os_domain\n" \
    "region=$os_region\n" \
    "tenant-name=$os_tenant_name\n"


class CloudMan2AnsibleAppConfigurer(AnsibleAppConfigurer):
    """Add CloudMan2 specific vars to playbook."""

    def _gen_cloud_conf(self, cloud_provider, cloud_config):
        zone = cloud_config.get('target', {}).get('target_zone', {})
        creds = cloud_config.get('credentials', {})

        if cloud_provider == "aws":
            conf_template = AWS_CLOUD_CONF
            values = {}
        elif cloud_provider == "azure":
            conf_template = AZURE_CLOUD_CONF
            values = {}
        elif cloud_provider == "gcp":
            # https://github.com/rancher/rke/issues/1329
            conf_template = GCP_CLOUD_CONF
            values = {}
        elif cloud_provider == "openstack":
            conf_template = OPENSTACK_CLOUD_CONF
            values = {
                'os_username': creds.get('os_username'),
                'os_password': creds.get('os_password'),
                'os_domain': creds.get('os_project_domain_name'),
                'os_tenant_name': creds.get('os_project_name'),
                'os_auth_url': zone.get('cloud', {}).get('auth_url'),
                'os_region': zone.get('region', {}).get('name')
            }
        return string.Template(conf_template).substitute(values)

    def _get_kube_cloud_settings(self, cloud_config):
        cb_cloud_provider = cloud_config.get('credentials', {}).get('cloud_id')
        CB_CLOUD_TO_KUBE_CLOUD_MAP = {
            'aws': 'aws',
            'openstack': 'openstack',
            'azure': 'azure',
            'gcp': 'gce'
        }
        return (CB_CLOUD_TO_KUBE_CLOUD_MAP.get(cb_cloud_provider),
                self._gen_cloud_conf(cb_cloud_provider, cloud_config))

    def configure(self, app_config, provider_config):
        host = provider_config.get('host_config', {}).get('host_address')
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
        cloud_config = provider_config.get('cloud_config', {})
        cm_initial_cluster_data = {
            'cloud_config': cloud_config,
            'host_config': provider_config.get('host_config'),
            'app_config': app_config
        }
        kube_cloud_provider, kube_cloud_conf = self._get_kube_cloud_settings(
            cloud_config)
        playbook_vars = [
            ('cm_boot_image', app_config.get('config_cloudman2', {}).get(
                'cm_boot_image')),
            ('rancher_server', host),
            ('rancher_pwd', app_config.get('config_cloudman2', {}).get(
                'clusterPassword')),
            ('cm_initial_cluster_data', base64.b64encode(
                json.dumps(cm_initial_cluster_data).encode('utf-8')).decode('utf-8')),
            ('kube_cloud_provider', kube_cloud_provider),
            ('kube_cloud_conf', base64.b64encode(
                kube_cloud_conf.encode('utf-8')).decode('utf-8'))
        ]
        return super().configure(app_config, provider_config,
                                 playbook_vars=playbook_vars)
