"""Base VM plugin implementations."""
import copy
import ipaddress

import tenacity

from celery.utils.log import get_task_logger
from cloudbridge.base.helpers import generate_key_pair
from cloudbridge.interfaces import InstanceState
from cloudbridge.interfaces.exceptions import CloudBridgeBaseException
from cloudbridge.interfaces.resources import DnsRecordType
from cloudbridge.interfaces.resources import TrafficDirection

from cloudlaunch import configurers

from .app_plugin import AppPlugin

log = get_task_logger('cloudlaunch')


class InstanceNotDeleted(Exception):
    pass


class BaseVMAppPlugin(AppPlugin):
    """
    Implementation for the basic VM app.

    It is expected that other apps inherit this class and override or
    complement methods provided here.
    """

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
        vmfs = provider.security.vm_firewalls.find(label=vmf_name)
        # First, look for firewall with the same associated network
        vm = None
        if vmfs:
            for vmf in vmfs:
                if vmf.network_id == network_id:
                    return vmf
                if not vmf.network_id and not vm:
                    vm = vmf
            # If none are found with the same network id, return the first one
            # with no associated network
            if vm:
                return vm
            # If none are found with no associated network, return the first
            # with the same label disregarding network association
            return vmfs[0]
        # If none are found, create one
        return provider.security.vm_firewalls.create(
            label=vmf_name, network=network_id, description=description)

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

    def _attach_public_ip(self, provider, inst, network_id):
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
            gateway = net.gateways.get_or_create()
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

    def _configure_vm_firewalls(self, provider, subnet, firewall):
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


    def _get_or_create_default_subnet(self, provider, network_id, placement):
        """
        Figure out a subnet matching the supplied constraints.

        Note that the supplied arguments may be given as ``None``.
        """
        if network_id:
            net = provider.networking.networks.get(network_id)
            for sn in net.subnets:
                # No placement necessary; pick a (random) subnet
                if not placement:
                    return sn
                # Placement match is necessary
                elif sn.zone == placement:
                    return sn
        if not placement:
            placement = ''  # placement needs to be a str
        sn = provider.networking.subnets.get_or_create_default()
        return sn

    def _setup_networking(self, provider, net_id, subnet_id, placement):
        log.debug("Setting up networking for net %s, sn %s, in zone %s",
                  net_id, subnet_id, placement)
        if subnet_id:
            subnet = provider.networking.subnets.get(subnet_id)
        else:
            subnet = self._get_or_create_default_subnet(
                provider, net_id, placement)
        # Make sure the subnet has Internet connectivity
        try:
            found_routers = [router for router in provider.networking.routers
                             if router.network_id == subnet.network_id]
            # Check if the subnet's network is connected to a router
            router = None
            for r in found_routers:
                is_attached = bool([sn for sn in r.subnets
                                    if sn.id == subnet.id])
                if is_attached:
                    router = r
                    break
            # Create a new router if not
            if not router:
                router_name = 'cl-router-%s' % subnet.network.name
                log.debug("Creating CloudLaunch router %s", router_name)
                router = provider.networking.routers.create(
                    label=router_name, network=subnet.network_id)

            # Attach a gateway to the router
            net = provider.networking.networks.get(subnet.network_id)
            log.debug("Creating inet gateway for net %s", net.id)
            gw = net.gateways.get_or_create()
            router.attach_gateway(gw)
            try:
                for sn in subnet.network.subnets:
                    router.attach_subnet(sn)
            except Exception as e:
                log.debug("Couldn't attach subnet; ignoring: %s", e)
        except Exception as e:
            # Creating a router/gateway may not work with classic
            # networking so ignore errors if they occur.
            log.debug("Couldn't create router or gateway; ignoring: %s", e)
        return subnet

    def _resolve_launch_properties(self, provider, cloudlaunch_config):
        """
        Resolve inter-dependent launch properties.

        Subnet, Placement, and VM Firewalls have launch dependencies among
        themselves so deduce what does are.
        """
        net_id = cloudlaunch_config.get('network', None)
        subnet_id = cloudlaunch_config.get('subnet', None)
        placement = provider.zone_name
        try:
            subnet = self._setup_networking(provider, net_id, subnet_id, placement)
        except CloudBridgeBaseException as e:
            if provider.PROVIDER_ID == 'openstack':
                # On OpenStack NeCTAR for example, legacy networking may
                # be able to continue despite the exception, so try with empty
                # subnet
                log.exception(e)
                subnet = None
            else:
                raise

        vmf = None
        if cloudlaunch_config.get('firewall'):
            vmf = self._configure_vm_firewalls(
                provider, subnet, cloudlaunch_config['firewall'])
        return subnet, placement, vmf

    def deploy(self, name, task, app_config, provider_config):
        """See the parent class in ``app_plugin.py`` for the docstring."""
        p_result = {}
        c_result = {}
        app_config['deployment_config'] = {
            'name': name
        }
        if provider_config.get('host_config'):
            # A host is provided; use CloudLaunch's default published ssh key
            pass  # Implement this once we actually support it
        else:
            host_config = {}
            if app_config.get('config_appliance'):
                # Host config will take place; generate a tmp ssh config key
                public_key, private_key = generate_key_pair()
                host_config = {
                    'ssh_private_key': private_key,
                    'ssh_public_key': public_key,
                    'ssh_user': app_config.get(
                        'config_appliance', {}).get('sshUser'),
                    'run_cmd': app_config.get(
                        'config_appliance', {}).get('runCmd')
                }
                provider_config['host_config'] = host_config
            p_result = self._provision_host(name, task, app_config,
                                            provider_config)
            host_config['host_address'] = p_result['cloudLaunch'].get(
                'hostname')
            host_config['public_ip'] = p_result['cloudLaunch'].get(
                'publicIP')
            host_config['private_ip'] = p_result['cloudLaunch'].get(
                'private_ip')
            host_config['instance_id'] = p_result['cloudLaunch'].get(
                'instance').get('id')

        if app_config.get('config_appliance'):
            try:
                c_result = self._configure_host(name, task, app_config,
                                                provider_config)
            except Exception:
                # cleanup instance
                if host_config.get('instance_id'):
                    provider = provider_config.get('cloud_provider')
                    hostname_config = app_config.get(
                        "config_cloudlaunch", {}).get('hostnameConfig')
                    self._cleanup_instance(
                        provider, host_config['instance_id'], hostname_config)
                raise
        # Merge result dicts; right-most dict keys take precedence
        return {'cloudLaunch': {**p_result.get('cloudLaunch', {}),
                                **c_result.get('cloudLaunch', {})}}

    def _cleanup_hostname(self, provider, hostname_config):
        if hostname_config and hostname_config.get('hostnameType') == 'cloud_dns':
            dns_zone = hostname_config.get('dnsZone')
            dns_rec_name = hostname_config.get('dnsRecordName')
            dns_zone = provider.dns.host_zones.get(dns_zone.get('id'))
            host_name = (dns_rec_name + "." + dns_zone.name
                         if dns_rec_name else dns_zone.name)
            try:
                # Also delete wildcard record
                dns_recs = dns_zone.records.find(name="*." + host_name)
                for dns_rec in dns_recs:
                    dns_rec.delete()
            finally:
                dns_recs = dns_zone.records.find(name=host_name)
                for dns_rec in dns_recs:
                    dns_rec.delete()

    @tenacity.retry(stop=tenacity.stop_after_attempt(7),
                    wait=tenacity.wait_exponential(multiplier=1, min=4, max=256),
                    reraise=True,
                    after=lambda *args: log.debug("Instance not deleted, retrying......"))
    def _cleanup_instance(self, provider, instance_id, hostname_config):
        log.debug("Deleting deployment instance %s", instance_id)
        try:
            self._cleanup_hostname(provider, hostname_config)
        except Exception:
            log.exception("Could not cleanup DNS")

        inst = provider.compute.instances.get(instance_id)
        if inst:
            inst.delete()
            inst.wait_for([InstanceState.DELETED, InstanceState.UNKNOWN],
                          terminal_states=[InstanceState.ERROR])

        # instance should no longer exist

        inst = provider.compute.instances.get(instance_id)
        if not inst:
            return True
        elif inst.state in (InstanceState.DELETED, InstanceState.UNKNOWN):
            return True
        else:
            raise InstanceNotDeleted(
                f"Instance {instance_id} should have been deleted but still exists.")

    def _provision_host(self, name, task, app_config, provider_config):
        """Provision a host using the provider_config info."""
        cloudlaunch_config = app_config.get("config_cloudlaunch", {})
        provider = provider_config.get('cloud_provider')
        extra_provider_args = provider_config.get('extra_provider_args') or {}
        cloud_config = provider_config.get('cloud_config')
        host_config = provider_config.get('host_config', {})
        user_data = provider_config.get('cloud_user_data') or ""
        user_data = user_data if isinstance(user_data, str) else ""

        custom_image_id = cloudlaunch_config.get("customImageID", None)
        img = provider.compute.images.get(
            custom_image_id or cloud_config.get('image', {}).get('image_id'))
        task.update_state(state='PROGRESSING',
                          meta={'action': "Retrieving or creating a key pair"})
        kp = self._get_or_create_kp(provider,
                                    cloudlaunch_config.get('keyPair') or
                                    'cloudlaunch-key-pair')
        task.update_state(state='PROGRESSING',
                          meta={'action': "Applying firewall settings"})
        subnet, placement_zone, vmfl = self._resolve_launch_properties(
            provider, cloudlaunch_config)
        cb_launch_config = self._get_cb_launch_config(provider, img,
                                                      cloudlaunch_config)
        vm_type = cloudlaunch_config.get('vmType')

        log.debug("Launching with subnet %s and VM firewalls %s", subnet, vmfl)

        if host_config.get('ssh_public_key') or host_config.get(
                'run_cmd'):
            user_data += """
#cloud-config
"""
        if host_config.get('ssh_public_key'):
            # cloud-init config to allow login w/ the config ssh key
            # http://cloudinit.readthedocs.io/en/latest/topics/examples.html
            log.info("Adding a cloud-init config public ssh key to user data")
            user_data += """
ssh_authorized_keys:
    - {0}""".format(host_config['ssh_public_key'])
        if host_config.get('run_cmd'):
            user_data += """
runcmd:"""
            for rc in host_config.get('run_cmd'):
                user_data += """
 - {0}
 """.format(rc.split(" "))
        log.info("Launching base_vm of type %s with UD:\n%s", vm_type,
                 user_data)
        task.update_state(state="PROGRESSING",
                          meta={"action": "Launching an instance of type %s "
                                          "with keypair %s in zone %s" %
                                          (vm_type, kp.name, placement_zone)})
        inst = provider.compute.instances.create(
            label=name, image=img, vm_type=vm_type, subnet=subnet,
            key_pair=kp, vm_firewalls=vmfl,
            user_data=user_data, launch_config=cb_launch_config,
            **extra_provider_args)
        task.update_state(state="PROGRESSING",
                          meta={"action": "Waiting for instance %s" % inst.id})
        log.debug("Waiting for instance {0} to be ready...".format(inst.id))
        try:
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
            if vmfl:
                results['securityGroup'] = {'id': vmfl[0].id, 'name': vmfl[0].name}
            results['instance'] = {'id': inst.id}
            if not cloudlaunch_config.get('skip_floating_ip'):
                results['publicIP'] = self._attach_public_ip(
                    provider, inst, subnet.network_id if subnet else None)
            results['private_ip'] = inst.private_ips[0] if inst.private_ips else results['publicIP']
            # Configure hostname (if set)
            results['hostname'] = self._configure_hostname(
                provider, results['private_ip'], cloudlaunch_config.get('hostnameConfig'))
            task.update_state(
                state='PROGRESSING',
                meta={"action": "Instance created successfully. " +
                                f"Public IP: {results.get('publicIP') or results.get('private_ip')}"})
            return {"cloudLaunch": results}
        except Exception:
            # We send a null hostname config since we don't want to delete existing
            # hostnames
            self._cleanup_instance(provider, inst.id, None)
            raise

    def _configure_hostname(self, provider, public_ip, hostname_config):
        if not hostname_config:
            return public_ip
        elif hostname_config.get('hostnameType') == 'cloud_dns':
            dns_zone = hostname_config.get('dnsZone')
            dns_rec_name = hostname_config.get('dnsRecordName')
            try:
                dns_zone = provider.dns.host_zones.get(dns_zone.get('id'))
                host_name = (dns_rec_name + "." + dns_zone.name
                             if dns_rec_name else dns_zone.name)
                dns_zone.records.create(host_name, DnsRecordType.A, [public_ip])
                # Also create wildcard record
                dns_zone.records.create("*." + host_name, DnsRecordType.A, [public_ip])
                return host_name.rstrip(".")
            except CloudBridgeBaseException:
                log.exception("Error while creating cloud dns records")
                return public_ip
        elif hostname_config.get('hostnameType') == 'manual':
            return hostname_config.get('hostName') or public_ip
        else:
            return public_ip

    def _configure_host(self, name, task, app_config, provider_config):
        try:
            configurer = self._get_configurer(app_config)
        except Exception as e:
            task.update_state(
                state='ERROR',
                meta={'action':
                      "Unable to create app configurer: {}".format(e)}
            )
            raise
        task.update_state(
            state='PROGRESSING',
            meta={'action': 'Validating provider connection info...'}
        )
        try:
            configurer.validate(app_config, provider_config)
        except Exception as e:
            task.update_state(
                state='ERROR',
                meta={'action': "Validation of provider connection info "
                                "failed: {}".format(e)}
            )
            raise
        task.update_state(
            state='PROGRESSING',
            meta={'action': 'Configuring application...'}
        )
        try:
            result = configurer.configure(app_config, provider_config)
            task.update_state(
                state='PROGRESSING',
                meta={'action': 'Application configuration completed '
                                'successfully.'}
            )
            return result
        except Exception as e:
            task.update_state(
                state='ERROR',
                meta={'action': "Configuration failed: {}".format(e)}
            )
            raise

    def _get_configurer(self, app_config):
        return configurers.create_configurer(app_config)

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
        as deleted or disappears from the provider.

        *Note* that this method will delete resource(s) associated with
        the deployment - this is an un-recoverable action.
        """
        instance_id = self._get_deployment_iid(deployment)
        if not instance_id:
            return False
        hostname_config = deployment.get('launch_result', {}).get(
            'cloudLaunch', {}).get('hostNameConfig', {})
        return self._cleanup_instance(provider, instance_id, hostname_config)
