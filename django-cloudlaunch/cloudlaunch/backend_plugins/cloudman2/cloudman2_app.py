"""CloudMan 2.0 application plugin implementation."""
import pathlib
import random
import time
import secrets
import string
import yaml
from urllib.parse import urljoin

from celery.utils.log import get_task_logger

import tenacity

from cloudbridge.base.helpers import cleanup_action

from cloudlaunch.configurers import AnsibleAppConfigurer

from cloudlaunch.backend_plugins.simple_web_app import SimpleWebAppPlugin

log = get_task_logger('cloudlaunch')


def get_iam_handler_for(provider_id):
    if provider_id == "aws":
        return AWSKubeIAMPolicyHandler
    elif provider_id == "gcp":
        return GCPKubeIAMPolicyHandler
    else:
        return None


class AWSKubeIAMPolicyHandler(object):

    def __init__(self, provider, dpl_name, app_config):
        self.provider = provider
        self._dpl_name = dpl_name
        self.app_config = app_config
        iam_resource = self.provider.session.resource('iam')
        self.iam_client = iam_resource.meta.client

    @property
    def dpl_name(self):
        return self._dpl_name

    def _get_or_create_iam_policy(self, policy_name, policy_doc):
        # To require lower IAM permissions, explicitly check whether
        # the policy exists, rather than trying to create it and catching
        # the EntityAlreadyExistsException. This way, the create permission
        # is not needed for worker nodes since the master would have already
        # created the policy. Yet, check for the EntityAlreadyExistsException
        # anyway to avoid race conditions.
        policy_arn = None
        try:
            sts = self.provider.session.client('sts')
            account_id = sts.get_caller_identity()['Account']
            policy_arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
            response = self.iam_client.get_policy(PolicyArn=policy_arn)
            return response['Policy']['Arn']
        except self.iam_client.exceptions.NoSuchEntityException:
            try:
                response = self.iam_client.create_policy(
                    PolicyName=policy_name,
                    PolicyDocument=policy_doc
                )
                policy_arn = response.get('Policy').get('Arn')
                waiter = self.iam_client.get_waiter('policy_exists')
                waiter.wait(PolicyArn=policy_arn)
                return policy_arn
            except self.iam_client.exceptions.EntityAlreadyExistsException:
                return policy_arn

    def _delete_iam_policy(self, policy_arn):
        self.iam_client.delete_policy(PolicyArn=policy_arn)

    def _load_policy_relative(self, policy_path_relative):
        path = (pathlib.Path(__file__).parent / policy_path_relative)
        with open(path) as f:
            return f.read()

    def _get_or_create_cm2_iam_policy(self):
        policy_name = 'cm2-kube-policy'
        policy_doc = self._load_policy_relative(
            'rancher2_aws_iam_policy.json')
        return self._get_or_create_iam_policy(policy_name, policy_doc)

    def _get_or_create_iam_role(self, role_name, trust_policy):
        try:
            response = self.iam_client.get_role(RoleName=role_name)
            return response['Role']['RoleName']
        except self.iam_client.exceptions.NoSuchEntityException:
            try:
                self.iam_client.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=trust_policy,
                    Description="CloudMan2 IAM role for rancher/kubernetes")
                waiter = self.iam_client.get_waiter('role_exists')
                waiter.wait(RoleName=role_name)
                return role_name
            except self.iam_client.exceptions.EntityAlreadyExistsException:
                return role_name

    def _delete_iam_role(self, role_name):
        self.iam_client.delete_role(RoleName=role_name)

    def _get_or_create_cm2_iam_role(self):
        role_name = self.dpl_name + "-cm2-kube-role"
        if "cn" in self.provider.region_name:
            policy_path = 'rancher2_aws_iam_trust_policy-cn.json'
        else:
            policy_path = 'rancher2_aws_iam_trust_policy.json'
        trust_policy = self._load_policy_relative(policy_path)
        return self._get_or_create_iam_role(role_name, trust_policy)

    @tenacity.retry(stop=tenacity.stop_after_attempt(5),
                    wait=tenacity.wait_fixed(5),
                    reraise=True)
    def _attach_policy_to_role(self, role, policy):
        self.iam_client.attach_role_policy(
            RoleName=role,
            PolicyArn=policy
        )

    def _detach_policy_from_role(self, role, policy_arn):
        self.iam_client.detach_role_policy(
            RoleName=role,
            PolicyArn=policy_arn
        )

    def _get_or_create_instance_profile(self, profile_name):
        try:
            self.iam_client.get_instance_profile(
                InstanceProfileName=profile_name)
            return profile_name
        except self.iam_client.exceptions.NoSuchEntityException:
            try:
                self.iam_client.create_instance_profile(
                    InstanceProfileName=profile_name)
                waiter = self.iam_client.get_waiter('instance_profile_exists')
                waiter.wait(InstanceProfileName=profile_name)
                # Despite the waiter, aws run_instances sometimes take a while
                # to recognize that the profile exists, so sleep manually as a
                # workaround
                time.sleep(5)
                return profile_name
            except self.iam_client.exceptions.EntityAlreadyExistsException:
                return profile_name

    def _delete_instance_profile(self, profile_name):
        self.iam_client.delete_instance_profile(
            InstanceProfileName=profile_name)

    def _get_or_create_cm2_instance_profile(self):
        profile_name = self.dpl_name + '-cm2-kube-role'
        return self._get_or_create_instance_profile(profile_name)

    @tenacity.retry(stop=tenacity.stop_after_attempt(5),
                    wait=tenacity.wait_fixed(5),
                    reraise=True)
    def _attach_role_to_instance_profile(self, profile_name, role):
        try:
            self.iam_client.add_role_to_instance_profile(
                InstanceProfileName=profile_name,
                RoleName=role
            )
        except self.iam_client.exceptions.LimitExceededException:
            log.debug("Instance profile is already associated with role.")
            pass

    def _detach_role_from_instance_profile(self, profile_name, role):
        self.iam_client.remove_role_from_instance_profile(
            InstanceProfileName=profile_name,
            RoleName=role
        )

    def _configure_instance_profile(self):
        role = self._get_or_create_cm2_iam_role()
        inst_profile = self._get_or_create_cm2_instance_profile()
        self._attach_role_to_instance_profile(inst_profile, role)
        policy = self._get_or_create_cm2_iam_policy()
        self._attach_policy_to_role(role, policy)
        return inst_profile

    def create_iam_policy(self):
        inst_profile = self._configure_instance_profile()
        return {
            'iam_instance_profile': {
                'Name': inst_profile
            }
        }

    def cleanup_iam_policy(self):
        sts = self.provider.session.client('sts')
        account_id = sts.get_caller_identity()['Account']
        policy_arn = f'arn:aws:iam::{account_id}:policy/cm2-kube-policy'
        role_name = self.dpl_name + "-cm2-kube-role"
        profile_name = self.dpl_name + '-cm2-kube-role'

        with cleanup_action(lambda: self._delete_iam_role(
                self.dpl_name + "-cm2-kube-role")):
            with cleanup_action(lambda: self._delete_instance_profile(
                    self.dpl_name + '-cm2-kube-role')):
                with cleanup_action(
                        lambda: self._detach_role_from_instance_profile(
                            profile_name, role_name)):
                    with cleanup_action(lambda: self._delete_iam_policy(
                            policy_arn)):
                        with cleanup_action(
                                lambda: self._detach_policy_from_role(
                                    role_name, policy_arn)):
                            pass


class GCPKubeIAMPolicyHandler(object):

    def __init__(self, provider, dpl_name, app_config):
        self.provider = provider
        self._dpl_name = dpl_name
        self.app_config = app_config

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
        app_config = super(CloudMan2AppPlugin, CloudMan2AppPlugin).sanitise_app_config(app_config)
        app_config['config_cloudman2']['clusterPassword'] = '********'
        return app_config

    def _get_iam_handler(self, provider):
        """ This function is used to enable subclassses to override behaviour"""
        return get_iam_handler_for(provider.PROVIDER_ID)

    def _provision_host(self, name, task, app_config, provider_config):
        provider = provider_config.get('cloud_provider')
        handler_class = self._get_iam_handler(provider)
        if handler_class:
            provider = provider_config.get('cloud_provider')
            handler = handler_class(provider, name, app_config)
            provider_config['extra_provider_args'] = \
                handler.create_iam_policy()
        return super()._provision_host(name, task, app_config, provider_config)

    def _configure_host(self, name, task, app_config, provider_config):
        result = super()._configure_host(name, task, app_config, provider_config)
        host = provider_config.get('host_config', {}).get('host_address')
        pulsar_token = app_config.get('config_cloudman2', {}).get('pulsar_token')
        result['cloudLaunch'] = {'applicationURL':
                                 'https://{0}/'.format(host),
                                 'pulsar_token': pulsar_token}
        task.update_state(
            state='PROGRESSING',
            meta={'action': "Waiting for CloudMan to become available at %s"
                            % result['cloudLaunch']['applicationURL']})
        login_url = urljoin(result['cloudLaunch']['applicationURL'],
                            'cloudman/oidc/authenticate')
        self.wait_for_http(login_url, ok_status_codes=[302, 200])
        return result

    def _get_configurer(self, app_config):
        # CloudMan2 can only be configured with ansible
        return CloudMan2AnsibleAppConfigurer()

    def delete(self, provider, deployment):
        def delete_iam():
            handler_class = self._get_iam_handler(provider)
            if handler_class:
                handler = handler_class(provider, deployment.get('name'), {})
                handler.cleanup_iam_policy()

        with cleanup_action(delete_iam):
            return super().delete(provider, deployment)


AWS_CLOUD_CONF = \
    "[Global]\n"

AZURE_CLOUD_CONF = \
"""
{
  "cloud": "",
  "tenantId": "$tenantId",
  "subscriptionId": "$subscriptionId",
  "resourceGroup": "$resourceGroup",
  "aadClientId": "$aadClientID",
  "aadClientSecret": "$aadClientSecret",
  # "location": "eastus",
  # "vnetName": "cloudbridge-net-d25005",
  # "vnetResourceGroup": "$resourceGroup",
  # "subnetName": "cloudbridge-subnet-09f56a",
  # "securityGroupName": "cloudlaunch-cm2-3c7735",
  # "routeTableName": "",
  # "primaryAvailabilitySetName": "",
  # "vmType": "",
  # "primaryScaleSetName": "",
  # "aadClientCertPath": "",
  # "aadClientCertPassword": "",
  # "cloudProviderBackoff": false,
  # "cloudProviderBackoffRetries": 0,
  # "cloudProviderBackoffExponent": 0,
  # "cloudProviderBackoffDuration": 0,
  # "cloudProviderBackoffJitter": 0,
  # "cloudProviderRateLimit": false,
  # "cloudProviderRateLimitQPS": 0,
  # "cloudProviderRateLimitBucket": 0,
  # "useInstanceMetadata": true,
  # "useManagedIdentityExtension": false,
  # "maximumLoadBalancerRuleCount": 0
}\n
"""

GCP_CLOUD_CONF = \
    "[Global]\n"

OPENSTACK_CLOUD_CONF = \
    "[Global]\n" \
    "username=\"$os_username\"\n" \
    "password=\"$os_password\"\n" \
    "auth-url=$os_auth_url\n" \
    "$domain_entry\n" \
    "region=$os_region\n" \
    "tenant-name=\"$os_tenant_name\"\n" \
    "[BlockStorage]\n" \
    "ignore-volume-az=$os_ignore_volume_az\n"


class CloudMan2AnsibleAppConfigurer(AnsibleAppConfigurer):
    """Add CloudMan2 specific vars to playbook."""

    def _os_ignore_az(self, compute_zone, cb_settings):
        # We use a simple comparison here to determine whether or not k8s
        # should match compute zone name and storage zone name when
        # fulfilling PVCs. If they mismatch in our mappings, then k8s too
        # should ignore az. However, this may not work for all openstack
        # configurations, but should do for the two common cases, where there's
        # either one storage zone for all compute zones, or a unique storage
        # zone per compute zone.
        settings = (yaml.safe_load(cb_settings)
                    if cb_settings else {})
        zone_mappings = settings.get('zone_mappings', {})
        storage_zone = zone_mappings.get(compute_zone, {}).get(
            'os_storage_zone_name')
        return compute_zone != storage_zone

    def _gen_cloud_conf(self, provider_id, cloud_config):
        zone = cloud_config.get('target', {}).get('target_zone', {})
        creds = cloud_config.get('credentials', {})

        if provider_id == "aws":
            conf_template = AWS_CLOUD_CONF
            values = {}
        elif provider_id == "azure":
            # https://gist.github.com/jgreat/a0b57ddcdc1dc1d9aaef52d6dd4c9c6a
            # https://rancher.com/docs/rancher/v2.x/en/cluster-provisioning/rke-clusters/options/cloud-providers/
            conf_template = AZURE_CLOUD_CONF
            values = {
                'tenantId': creds.get('azure_tenant'),
                'aadClientID': creds.get('azure_client_id'),
                'aadClientSecret': creds.get('azure_secret'),
                'subscriptionId': creds.get('azure_subscription_id'),
                'resourceGroup': creds.get('azure_resource_group')
            }
        elif provider_id == "gcp":
            # https://github.com/rancher/rke/issues/1329
            # https://github.com/rancher/rancher/issues/4711
            conf_template = GCP_CLOUD_CONF
            values = {}
        elif provider_id == "openstack":
            # http://henriquetruta.github.io/openstack-cloud-provider/
            conf_template = OPENSTACK_CLOUD_CONF
            os_ignore_az = self._os_ignore_az(
                zone.get('zone_id'),
                zone.get('region', {}).get('cloudbridge_settings'))
            if creds.get('os_user_domain_id'):
                domain_entry = f"domain-id={creds.get('os_user_domain_id')}"
            else:
                domain_entry = f"domain-name={creds.get('os_user_domain_name')}"

            values = {
                'os_username': creds.get('os_username'),
                'os_password': creds.get('os_password'),
                'domain_entry': domain_entry,
                'os_tenant_name': creds.get('os_project_name'),
                'os_auth_url': zone.get('cloud', {}).get('auth_url'),
                'os_region': zone.get('region', {}).get('name'),
                # https://github.com/kubernetes/kubernetes/issues/53488
                'os_ignore_volume_az': os_ignore_az
            }
        return string.Template(conf_template).substitute(values)

    def _get_kube_cloud_settings(self, provider_config, cloud_config):
        provider_id = provider_config.get('cloud_provider').PROVIDER_ID
        CB_CLOUD_TO_KUBE_CLOUD_MAP = {
            'aws': 'aws',
            'openstack': 'openstack',
            'azure': 'azure',
            'gcp': 'gce'
        }
        return (CB_CLOUD_TO_KUBE_CLOUD_MAP.get(provider_id),
                self._gen_cloud_conf(provider_id, cloud_config))

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
            provider_config, cloud_config)

        cm_playbook_vars = {
            'cluster_hostname': host,
            'cluster_password': app_config.get('config_cloudman2', {})
                .get('clusterPassword', ''),
            'kube_cloud_provider': kube_cloud_provider,
            'kube_cloud_conf': kube_cloud_conf,
            'cm_skip_cloudman': str(app_config.get('config_cloudman2', {})
                .get('cm_skip_cloudman', 'false')),
            'cm_deployment_name': app_config.get('deployment_config', {})
                .get('name', ''),
            'cm_initial_cluster_data': cm_initial_cluster_data,
            'cm_chart_version': str(app_config.get('config_cloudman2', {})
                .get('cm_chart_version', '')),
            'cm_charts_repo': str(app_config.get('config_cloudman2', {})
                .get('cm_charts_repo', '')),
            'cm_initial_storage_size': str(app_config.get('config_cloudman2', {})
                .get('cm_initial_storage_size', '')),
            'cm_helm_values': app_config.get('config_cloudman2', {})
                .get('cm_helm_values', {}),
            'rke_registration_token': secrets.token_urlsafe()
        }
        # Allow playbook vars to be overridden
        cm_playbook_vars.update(app_config.get('config_cloudman2', {})
                                .get('cm_playbook_vars', {}))
        # pop unneeded values to prevent recursion/self-referential jinja templates
        app_config.pop('config_cloudman2')

        return super().configure(app_config, provider_config,
                                 playbook_vars=cm_playbook_vars)
