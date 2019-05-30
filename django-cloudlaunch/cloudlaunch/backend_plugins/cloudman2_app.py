"""CloudMan 2.0 application plugin implementation."""
import json
import pathlib
import random
import string
import base64
from urllib.parse import urljoin

from celery.utils.log import get_task_logger

from cloudlaunch.configurers import AnsibleAppConfigurer

from .simple_web_app import SimpleWebAppPlugin

log = get_task_logger('cloudlaunch')


def get_iam_handler_for(provider_id):
    if provider_id == "aws":
        return AWSKubeIAMPolicyHandler
    elif provider_id == "gcp":
        return GCPKubeIAMPolicyHandler
    else:
        return None


class AWSKubeIAMPolicyHandler(object):

    def __init__(self, provider):
        self.provider = provider
        iam_resource = self.provider.session.resource('iam')
        self.iam_client = iam_resource.meta.client

    def _get_or_create_iam_policy(self):
        policy_name = 'cloudman2-kube-policy'
        try:
            policy_path = (pathlib.Path(__file__).parent /
                          'cloudman2/rancher2_aws_iam_policy.json')
            with open(policy_path) as f:
                policy_doc = json.load(f)
                response = self.iam_client.create_policy(
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(policy_doc)
                )
                return response.get('Policy').get('Arn')
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            sts = self.provider.session.client('sts')
            account_id = sts.get_caller_identity()['Account']
            policy_arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
            return policy_arn

    def _get_or_create_iam_role(self):
        role_name = "cloudman2-kube-role"
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "ec2.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        try:
            self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="CloudMan2 IAM role for rancher/kubernetes")
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            pass
        return role_name

    def _attach_policy_to_role(self, role, policy):
        self.iam_client.attach_role_policy(
            RoleName=role,
            PolicyArn=policy
        )

    def _get_or_create_instance_profile(self):
        profile_name = 'cloudman2-kube-inst-profile'
        try:
            response = self.iam_client.create_instance_profile(
                InstanceProfileName=profile_name)
            return response.get('InstanceProfile').get('Name')
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            return profile_name

    def _attach_role_to_instance_profile(self, profile_name, role):
        try:
            self.iam_client.add_role_to_instance_profile(
                InstanceProfileName=profile_name,
                RoleName=role
            )
        except self.iam_client.exceptions.LimitExceededException:
            log.debug("Instance profile is already associated with role.")
            pass

    def create_iam_policy(self):
        role = self._get_or_create_iam_role()
        policy = self._get_or_create_iam_policy()
        self._attach_policy_to_role(role, policy)
        inst_profile = self._get_or_create_instance_profile()
        self._attach_role_to_instance_profile(inst_profile, role)
        return {
            'iam_instance_profile': {
                'Name': inst_profile
            }
        }


class GCPKubeIAMPolicyHandler(object):

    def __init__(self, provider):
        self.provider = provider

    def create_iam_policy(self):
        return {
            'service_accounts': [{
                # pylint:disable=protected-access
                'email': self.provider._credentials.service_account_email,
                'scopes': [
                    'https://www.googleapis.com/auth/devstorage.read_write',
                    'https://www.googleapis.com/auth/logging.write',
                    'https://www.googleapis.com/auth/monitoring.write',
                    'https://www.googleapis.com/auth/service.management',
                    'https://www.googleapis.com/auth/servicecontrol',
                    'https://www.googleapis.com/auth/compute'
                ]
            }]
        }


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

    def _provision_host(self, name, task, app_config, provider_config):
        provider = provider_config.get('cloud_provider')
        handler_class = get_iam_handler_for(provider.PROVIDER_ID)
        if handler_class:
            provider = provider_config.get('cloud_provider')
            handler = handler_class(provider)
            provider_config['extra_provider_args'] = \
                handler.create_iam_policy()
        return super()._provision_host(name, task, app_config, provider_config)

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
            # https://gist.github.com/jgreat/a0b57ddcdc1dc1d9aaef52d6dd4c9c6a
            # https://rancher.com/docs/rancher/v2.x/en/cluster-provisioning/rke-clusters/options/cloud-providers/
            conf_template = AZURE_CLOUD_CONF
            values = {}
        elif cloud_provider == "gcp":
            # https://github.com/rancher/rke/issues/1329
            # https://github.com/rancher/rancher/issues/4711
            conf_template = GCP_CLOUD_CONF
            values = {}
        elif cloud_provider == "openstack":
            # http://henriquetruta.github.io/openstack-cloud-provider/
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
