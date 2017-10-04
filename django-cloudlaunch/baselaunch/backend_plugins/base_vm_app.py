"""Base VM plugin implementations."""
import copy
import time
import yaml

from cloudbridge.cloud.interfaces.resources import TrafficDirection
import requests
import requests.exceptions

from baselaunch import domain_model
from .app_plugin import AppPlugin

import logging
log = logging.getLogger(__name__)


class BaseVMAppPlugin(AppPlugin):
    """
    Implementation for the basic VM app.

    It is expected that other apps inherit this class and override or
    complement methods provided here.
    """

    def __init__(self):
        """Init any base app vars."""
        self.base_app = True

    @staticmethod
    def process_app_config(provider, name, cloud_config, app_config):
        """Extract any extra user data from the app config and return it."""
        return app_config.get("config_cloudlaunch", {}).get(
            "instance_user_data", {})

    @staticmethod
    def sanitise_app_config(app_config):
        """Return a sanitized copy of the supplied app config object."""
        return copy.deepcopy(app_config)

    def _get_or_create_kp(self, provider, kp_name):
        """Get or create an SSH key pair with the supplied name."""
        kps = provider.security.key_pairs.find(name=kp_name)
        if kps:
            return kps[0]
        else:
            log.debug("Creating key pair {0}".format(kp_name))
            return provider.security.key_pairs.create(name=kp_name)

    def _get_or_create_vmf(self, provider, subnet_id, vmf_name, description):
        """Fetch an existing VM firewall named ``vmf_name`` or create one."""
        vmf = provider.security.vm_firewalls.find(name=vmf_name)
        if len(vmf) > 0:
            return vmf[0]
        subnet = provider.networking.subnets.get(subnet_id)
        return provider.security.vm_firewalls.create(
            name=vmf_name, description=description,
            network_id=subnet.network_id)

    def _get_cb_launch_config(self, provider, image, cloudlaunch_config):
        """Compose a CloudBridge launch config object."""
        lc = None
        if cloudlaunch_config.get("rootStorageType", "instance") == "volume":
            if not lc:
                lc = provider.compute.instances.create_launch_config()
            lc.add_volume_device(source=image,
                                 size=int(cloudlaunch_config.get(
                                          "rootStorageSize", 20)),
                                 is_root=True)
        return lc

    def wait_for_http(self, url, max_retries=200, poll_interval=5):
        """Wait till app is responding at http URL."""
        count = 0
        while count < max_retries:
            time.sleep(poll_interval)
            try:
                r = requests.head(url)
                r.raise_for_status()
                return
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in (401, 403):
                    return
            except requests.exceptions.ConnectionError:
                pass
            count += 1

    def attach_public_ip(self, provider, inst):
        """
        If instance has no public IP, try to attach one.

        The method will attach a random floating IP that's available in the
        account. If there are no available IPs, try to allocate a new one.

        :rtype: ``str``
        :return: The attached IP address. This can be one that's already
                 available on the instance or one that has been attached.
        """
        if not inst.public_ips:
            fip = None
            for ip in provider.networking.floating_ips:
                if not ip.in_use:
                    fip = ip
                    break
            if fip:
                log.debug("Attaching an existing floating IP %s" %
                          fip.public_ip)
                inst.add_floating_ip(fip)
            else:
                fip = provider.networking.floating_ips.create()
                log.debug("Attaching a just-created floating IP %s" %
                          fip.public_ip)
                inst.add_floating_ip(fip)
            return fip.public_ip
        elif len(inst.public_ips) > 0:
            return inst.public_ips[0]
        else:
            return None

    def configure_vm_firewalls(self, provider, subnet_id, firewall):
        """
        Ensure any supplied firewall rules are represented in a VM Firewall.

        The following format is expected:

        ```
        "firewall": [
            {
                "rules": [
                    {
                        "from": "22",
                        "to": "22",
                        "cidr": "0.0.0.0/0",
                        "protocol": "tcp"
                    },
                    {
                        "src_group": "MyApp",
                        "from": "1",
                        "to": "65535",
                        "protocol": "tcp"
                    },
                    {
                        "src_group": 'bd9756b8-e9ab-41b1-8a1b-e466a04a997c',
                        "from": "22",
                        "to": "22",
                        "protocol": "tcp"
                    }
                ],
                "securityGroup": "MyApp",
                "description": "My App SG"
            }
        ]
        ```

        Note that if ``src_group`` is supplied, it must be either the current
        security group name or an ID of a different security group for which
        a rule should be added (i.e., different security groups cannot be
        identified by name and their ID must be used).

        :rtype: List of CloudBridge SecurityGroup
        :return: Security groups satisfying the constraints.
        """
        vmfl = []
        for group in firewall:
            # Get a handle on the SG
            vmf_name = group.get('securityGroup') or 'CloudLaunchDefault'
            vmf_desc = group.get('description') or 'Created by CloudLaunch'
            vmf = self._get_or_create_vmf(
                provider, subnet_id, vmf_name, vmf_desc)
            vmfl.append(vmf)
            # Apply firewall rules
            for rule in group.get('rules', []):
                try:
                    if rule.get('src_group'):
                        vmf.rules.create(TrafficDirection.INBOUND,
                                         rule.get('protocol'),
                                         rule.get('from_port'),
                                         rule.get('to_port'),
                                         src_dest_fw=vmf)
                    else:
                        vmf.rules.create(TrafficDirection.INBOUND,
                                         protocol=rule.get('protocol'),
                                         from_port=rule.get('from'),
                                         to_port=rule.get('to'),
                                         cidr=rule.get('cidr'))
                except Exception as e:
                    log.error("Exception applying firewall rules: %s" % e)
            return vmfl

    def get_or_create_subnet(self, provider, net_id=None, placement=None):
        """
        Figure out a subnet matching the supplied constraints.

        Any combination of the optional parameters is accepted.
        """
        if net_id:
            net = provider.networking.networks.get(net_id)
            for sn in net.subnets():
                # No placement necessary; pick a (random) subnet
                if not placement:
                    return sn
                # Placement match is necessary
                elif sn.zone == placement:
                    return sn
        sn = provider.networking.subnets.get_or_create_default(placement)
        return sn.id if sn else None

    def resolve_launch_properties(self, provider, cloudlaunch_config):
        """
        Resolve inter-dependent launch properties.

        Subnet, Placement, and VM Firewalls have launch dependencies among
        themselves so deduce what does are.
        """
        net_id = cloudlaunch_config.get('network', None)
        subnet_id = cloudlaunch_config.get('subnet', None)
        placement = cloudlaunch_config.get('placementZone', None)
        if not subnet_id:
            subnet_id = self.get_or_create_subnet(provider, net_id, placement)
        vmf = None
        if cloudlaunch_config.get('firewall', []):
            vmf = self.configure_vm_firewalls(
                provider, subnet_id, cloudlaunch_config.get('firewall', []))
        return subnet_id, placement, vmf

    def launch_app(self, provider, task, name, cloud_config,
                   app_config, user_data):
        """Initiate the app launch process."""
        cloudlaunch_config = app_config.get("config_cloudlaunch", {})
        custom_image_id = cloudlaunch_config.get("customImageID", None)
        img = provider.compute.images.get(
            custom_image_id or cloud_config.get('image_id'))
        task.update_state(state='PROGRESSING',
                          meta={'action': "Retrieving or creating a key pair"})
        kp = self._get_or_create_kp(provider,
                                    cloudlaunch_config.get('keyPair') or
                                    'cloudlaunch_key_pair')
        task.update_state(state='PROGRESSING',
                          meta={'action': "Applying firewall settings"})
        subnet_id, placement_zone, vmfl = self.resolve_launch_properties(
            provider, cloudlaunch_config)
        cb_launch_config = self._get_cb_launch_config(provider, img,
                                                      cloudlaunch_config)
        vm_type = cloudlaunch_config.get(
            'instanceType', cloud_config.get('default_instance_type'))

        log.debug("Launching with subnet %s and VM firewalls %s" %
                  (subnet_id, vmfl))
        log.info("Launching base_vm with UD:\n%s" % user_data)
        task.update_state(state='PROGRESSING',
                          meta={'action': "Launching an instance of type %s "
                                "with keypair %s in zone %s" %
                                (vm_type, kp.name, placement_zone)})
        inst = provider.compute.instances.create(
            name=name, image=img, vm_type=vm_type, subnet=subnet_id,
            key_pair=kp, vm_firewalls=vmfl, zone=placement_zone,
            user_data=user_data, launch_config=cb_launch_config)
        task.update_state(state='PROGRESSING',
                          meta={'action': "Waiting for instance %s" % inst.id})
        log.debug("Waiting for instance {0} to be ready...".format(inst.id))
        inst.wait_till_ready()
        static_ip = cloudlaunch_config.get('staticIP')
        if static_ip:
            task.update_state(state='PROGRESSING',
                              meta={'action': "Assigning requested floating "
                                    "IP: %s" % static_ip})
            inst.add_floating_ip(static_ip)
            inst.refresh()
        results = {}
        results['keyPair'] = {'id': kp.id, 'name': kp.name,
                              'material': kp.material}
        # FIXME: this does not account for multiple VM fw and expects one
        results['securityGroup'] = {'id': vmfl[0].id, 'name': vmfl[0].name}
        results['instance'] = {'id': inst.id}
        results['publicIP'] = self.attach_public_ip(provider, inst)
        task.update_state(
            state='PROGRESSING',
            meta={"action": "Instance created successfully. " +
                  "Public IP: %s" % results['publicIP'] if results['publicIP']
                  else ""})
        if self.base_app:
            if results['publicIP']:
                results['applicationURL'] = 'http://%s/' % results['publicIP']
                task.update_state(
                    state='PROGRESSING',
                    meta={'action': "Waiting for application to become ready "
                          "at %s" % results['applicationURL']})
                self.wait_for_http(results['applicationURL'])
            else:
                results['applicationURL'] = 'N/A'
        return {"cloudLaunch": results}

    def _get_deployment_iid(self, deployment):
        """
        Extract instance ID for the supplied deployment.

        We extract instance ID only for deployments in the SUCCESS state.

        @type  deployment: ``dict``
        @param deployment: A dictionary describing an instance of the
                           app deployment, requiring at least the following
                           keys: ``launch_status``, ``launch_result``.

        :rtype: ``str``
        :return: Provider-specific instance ID for the deployment or
                 ``None`` if instance ID not available.
        """
        if deployment.get('launch_status') == 'SUCCESS':
            return deployment.get('launch_result', {}).get(
                'cloudLaunch', {}).get('instance', {}).get('id')
        else:
            return None

    def health_check(self, provider, deployment):
        """Check the health of this app."""
        log.debug("Health check for deployment %s", deployment)
        iid = self._get_deployment_iid(deployment)
        if not iid:
            return {"instance_status": "unknown"}
        log.debug("Checking the status of instance %s", iid)
        inst = provider.compute.instances.get(iid)
        if inst:
            return {"instance_status": inst.state}
        else:
            return {"instance_status": "deleted"}

    def restart(self, provider, deployment):
        """Restart the app associated with the supplied deployment."""
        iid = self._get_deployment_iid(deployment)
        if not iid:
            return False
        log.debug("Restarting deployment instance %s", iid)
        inst = provider.compute.instances.get(iid)
        if inst:
            inst.reboot()
            return True
        # Instance does not exist so default to False
        return False

    def delete(self, provider, deployment):
        """
        Delete resource(s) associated with the supplied deployment.

        *Note* that this method will delete resource(s) associated with
        the deployment - this is an un-recoverable action.
        """
        iid = self._get_deployment_iid(deployment)
        if not iid:
            return False
        log.debug("Deleting deployment instance %s", iid)
        inst = provider.compute.instances.get(iid)
        if inst:
            inst.delete()
            return True
        # Instance does not exist so default to True
        return True
