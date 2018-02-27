"""Base VM plugin implementations."""
import copy
import time
import yaml
import ipaddress

from celery.utils.log import get_task_logger
from cloudbridge.cloud.base.helpers import generate_key_pair
from cloudbridge.cloud.interfaces import InstanceState
from cloudbridge.cloud.interfaces.resources import TrafficDirection

from .app_plugin import AppPlugin

log = get_task_logger('cloudlaunch')


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
    def validate_app_config(provider, name, cloud_config, app_config):
        """Extract any extra user data from the app config and return it."""
        return app_config.get("config_cloudlaunch", {}).get(
            "instance_user_data")

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

    def _get_or_create_vmf(self, provider, subnet, vmf_name, description):
        """
        Fetch an existing VM firewall named ``vmf_name`` or create one.

        The firewall must exist on the same network that the supplied subnet
        belongs to.
        """
        # Check for None in case of NeCTAR
        network_id = subnet.network_id if subnet else None
        for vmf in provider.security.vm_firewalls.find(name=vmf_name):
            # OpenStack doesn't have a network_id associated with the firewall, so
            # just return the first match
            if vmf.network_id is None or vmf.network_id == network_id:
                return vmf
        return provider.security.vm_firewalls.create(
            name=vmf_name, description=description,
            network_id=network_id)

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

    def attach_public_ip(self, provider, inst, network_id):
        """
        If instance has no public IP, try to attach one.

        The method will attach a random floating IP that's available in the
        account. If there are no available IPs, try to allocate a new one.

        :rtype: ``str``
        :return: The attached IP address. This can be one that's already
                 available on the instance or one that has been attached.
        """
        if len(inst.public_ips) > 0 and inst.public_ips[0]:
            return inst.public_ips[0]
        # Legacy NeCTAR support
        elif ipaddress.ip_address(inst.private_ips[0]).is_global:
            return inst.private_ips[0]
        else:
            fip = None
            net = provider.networking.networks.get(network_id)
            gateway = net.gateways.get_or_create_inet_gateway()
            for ip in gateway.floating_ips:
                if not ip.in_use:
                    fip = ip
                    break
            if fip:
                log.debug("Attaching an existing floating IP %s" %
                          fip.public_ip)
                inst.add_floating_ip(fip)
            else:
                fip = gateway.floating_ips.create()
                log.debug("Attaching a just-created floating IP %s" %
                          fip.public_ip)
                inst.add_floating_ip(fip)
            return fip.public_ip

    def configure_vm_firewalls(self, provider, subnet, firewall):
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
            vmf_name = group.get('securityGroup') or 'cloudlaunch'
            vmf_desc = group.get('description') or 'Created by CloudLaunch'
            vmf = self._get_or_create_vmf(
                provider, subnet, vmf_name, vmf_desc)
            vmfl.append(vmf)
            # Apply firewall rules
            for rule in group.get('rules', []):
                try:
                    if rule.get('src_group'):
                        vmf.rules.create(direction=TrafficDirection.INBOUND,
                                         protocol=rule.get('protocol'),
                                         from_port=int(rule.get('from')),
                                         to_port=int(rule.get('to')),
                                         src_dest_fw=vmf)
                    else:
                        vmf.rules.create(direction=TrafficDirection.INBOUND,
                                         protocol=rule.get('protocol'),
                                         from_port=int(rule.get('from')),
                                         to_port=int(rule.get('to')),
                                         cidr=rule.get('cidr'))
                except Exception as e:
                    log.error("Exception applying firewall rules: %s" % e)
            return vmfl

    def get_or_create_default_subnet(self, provider, net_id=None, placement=None):
        """
        Figure out a subnet matching the supplied constraints.

        Any combination of the optional parameters is accepted.
        """
        if net_id:
            net = provider.networking.networks.get(net_id)
            for sn in net.subnets:
                # No placement necessary; pick a (random) subnet
                if not placement:
                    return sn
                # Placement match is necessary
                elif sn.zone == placement:
                    return sn
        sn = provider.networking.subnets.get_or_create_default(placement)
        return sn

    def setup_networking(self, provider, net_id, subnet_id, placement):
        if subnet_id:
            subnet = provider.networking.subnets.get(subnet_id)
        else:
            subnet = self.get_or_create_default_subnet(
                provider, net_id, placement)
        if subnet:
            # Creating a router/gateway may not work with classic networking
            # so ignore errors if they occur
            try:
                router_name = 'cl_router_%s' % subnet.network_id
                found_routers = provider.networking.routers.find(
                    name=router_name)
                if found_routers:
                    router = found_routers[0]
                else:
                    router = provider.networking.routers.create(
                        network=subnet.network_id, name=router_name)
                try:
                    router.attach_subnet(subnet)
                except Exception as e:
                    log.debug("Couldn't attach subnet; ignoring: %s", e)
                net = provider.networking.networks.get(subnet.network_id)
                gw = net.gateways.get_or_create_inet_gateway(
                    'cloudlaunch-default-gateway')
                router.attach_gateway(gw)
            except Exception as e:
                log.debug("Couldn't create router or gateway; ignoring: %s", e)
        return subnet

    def resolve_launch_properties(self, provider, cloudlaunch_config):
        """
        Resolve inter-dependent launch properties.

        Subnet, Placement, and VM Firewalls have launch dependencies among
        themselves so deduce what does are.
        """
        net_id = cloudlaunch_config.get('network', None)
        subnet_id = cloudlaunch_config.get('subnet', None)
        placement = cloudlaunch_config.get('placementZone', None)
        subnet = self.setup_networking(provider, net_id, subnet_id, placement)
        vmf = None
        if cloudlaunch_config.get('firewall'):
            vmf = self.configure_vm_firewalls(
                provider, subnet, cloudlaunch_config['firewall'])
        return subnet, placement, vmf

    def deploy(self, name, task, app_config, provider_config):
        """See the parent class in ``app_plugin.py`` for the docstring."""
        p_result = {}
        c_result = {}
        if provider_config.get('host_address'):
            # A host is provided; use CloudLaunch's default published ssh key
            pass  # Implement this once we actually support it
        else:
            if app_config.get('config_appliance'):
                # Host config will take place; generate a tmp ssh config key
                public_key, private_key = generate_key_pair()
                provider_config['ssh_private_key'] = private_key
                provider_config['ssh_public_key'] = public_key
                provider_config['ssh_user'] = app_config.get(
                    'config_appliance', {}).get('sshUser')
            p_result = self._provision_host(name, task, app_config,
                                            provider_config)
            provider_config['host_address'] = p_result['cloudLaunch'].get(
                'publicIP')

        if app_config.get('config_appliance'):
            c_result = self._configure_host(name, task, app_config,
                                            provider_config)
        # Merge result dicts; right-most dict keys take precedence
        return {**p_result, **c_result}

    def _provision_host(self, name, task, app_config, provider_config):
        """Provision a host using the provider_config info."""
        cloudlaunch_config = app_config.get("config_cloudlaunch", {})
        provider = provider_config.get('cloud_provider')
        cloud_config = provider_config.get('cloud_config')
        user_data = provider_config.get('cloud_user_data') or ""

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
        subnet, placement_zone, vmfl = self.resolve_launch_properties(
            provider, cloudlaunch_config)
        cb_launch_config = self._get_cb_launch_config(provider, img,
                                                      cloudlaunch_config)
        vm_type = cloudlaunch_config.get(
            'vmType', cloud_config.get('default_instance_type'))

        log.debug("Launching with subnet %s and VM firewalls %s", subnet, vmfl)

        if provider_config.get('ssh_public_key'):
            # cloud-init config to allow login w/ the config ssh key
            # http://cloudinit.readthedocs.io/en/latest/topics/examples.html
            log.info("Adding a cloud-init config public ssh key to user data")
            user_data += """
#cloud-config
ssh_authorized_keys:
    - {0}""".format(provider_config['ssh_public_key'])
        log.info("Launching base_vm of type %s with UD:\n%s", vm_type,
                 user_data)
        task.update_state(state="PROGRESSING",
                          meta={"action": "Launching an instance of type %s "
                                          "with keypair %s in zone %s" %
                                          (vm_type, kp.name, placement_zone)})
        inst = provider.compute.instances.create(
            name=name, image=img, vm_type=vm_type, subnet=subnet,
            key_pair=kp, vm_firewalls=vmfl, zone=placement_zone,
            user_data=user_data, launch_config=cb_launch_config)
        task.update_state(state="PROGRESSING",
                          meta={"action": "Waiting for instance %s" % inst.id})
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
        # Support for legacy NeCTAR
        results['publicIP'] = self.attach_public_ip(
            provider, inst, subnet.network_id if subnet else None)
        task.update_state(
            state='PROGRESSING',
            meta={"action": "Instance created successfully. " +
                            "Public IP: %s" % results.get('publicIP') or ""})
        return {"cloudLaunch": results}

    def _configure_host(self, name, task, app_config, provider_config):
        host = provider_config.get('host_address')
        task.update_state(
            state='PROGRESSING',
            meta={"action": "Configuring host % s" % host})
        log.info("Configuring host %s", host)
        return {}

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
            return {"instance_status": "deployment_not_found"}
        log.debug("Checking the status of instance %s", iid)
        inst = provider.compute.instances.get(iid)
        if inst:
            return {"instance_status": inst.state}
        else:
            return {"instance_status": "not_found"}

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

        This is a blocking call that will wait until the instance is marked
        as deleted or dissapears from the provider.

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
            inst.wait_for([InstanceState.DELETED, InstanceState.UNKNOWN],
                          terminal_states=[InstanceState.ERROR])
            return True
        # Instance does not exist so default to True
        return True
