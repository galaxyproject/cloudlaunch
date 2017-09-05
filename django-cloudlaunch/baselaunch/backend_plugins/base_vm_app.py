"""Base VM plugin implementations."""
import copy
import time
import yaml

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
    def process_app_config(name, cloud_version_config, credentials,
                           app_config):
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

    def _get_or_create_sg(self, provider, subnet_id, sg_name, description):
        """Fetch an existing security group named ``sg_name`` or create one."""
        sgs = provider.security.security_groups.find(name=sg_name)
        if len(sgs) > 0:
            return sgs[0]
        # for sg1 in sgs:
        #     for sg2 in sgs:
        #         if sg1 == sg2:
        #             return sg1
        subnet = provider.networking.subnets.get(subnet_id)
        return provider.security.security_groups.create(
            name=sg_name, description=description,
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
            fips = provider.networking.networks.floating_ips
            for ip in fips:
                if not ip.in_use():
                    fip = ip
            if fip:
                log.debug("Attaching an existing floating IP %s" %
                          fip.public_ip)
                inst.add_floating_ip(fip.public_ip)
            else:
                fip = provider.networking.networks.create_floating_ip()
                log.debug("Attaching a just-created floating IP %s" %
                          fip.public_ip)
                inst.add_floating_ip(fip.public_ip)
            return fip.public_ip
        elif len(inst.public_ips) > 0:
            return inst.public_ips[0]
        else:
            return None

    def configure_security_groups(self, provider, subnet_id, firewall):
        """
        Ensure any supplied firewall rules are represented in a Security Group.

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
        sgs = []
        for group in firewall:
            # Get a handle on the SG
            sg_name = group.get('securityGroup') or 'CloudLaunchDefault'
            sg_desc = group.get('description') or 'Created by CloudLaunch'
            sg = self._get_or_create_sg(provider, subnet_id, sg_name, sg_desc)
            sgs.append(sg)
            # Apply firewall rules
            for rule in group.get('rules', []):
                try:
                    if rule.get('src_group'):
                        sg.add_rule(src_group=sg)
                    else:
                        sg.add_rule(ip_protocol=rule.get('protocol'),
                                    from_port=rule.get('from'),
                                    to_port=rule.get('to'),
                                    cidr_ip=rule.get('cidr'))
                except Exception as e:
                    log.error("Exception applying firewall rules: %s" % e)
            return sgs

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

        Subnet, Placement, and Security Groups have launch dependencies among
        themselves so deduce what does are.
        """
        net_id = cloudlaunch_config.get('network', None)
        subnet_id = cloudlaunch_config.get('subnet', None)
        placement = cloudlaunch_config.get('placementZone', None)
        if not subnet_id:
            subnet_id = self.get_or_create_subnet(provider, net_id, placement)
        sgs = None
        if cloudlaunch_config.get('firewall', []):
            sgs = self.configure_security_groups(
                provider, subnet_id, cloudlaunch_config.get('firewall', []))
        return subnet_id, placement, sgs

    def launch_app(self, task, name, cloud_version_config, credentials,
                   app_config, user_data):
        """Initiate the app launch process."""
        cloudlaunch_config = app_config.get("config_cloudlaunch", {})
        provider = domain_model.get_cloud_provider(cloud_version_config.cloud,
                                                   credentials)
        custom_image_id = cloudlaunch_config.get("customImageID", None)
        img = provider.compute.images.get(
            custom_image_id or cloud_version_config.image.image_id)
        task.update_state(state='PROGRESSING',
                          meta={'action': "Retrieving or creating a key pair"})
        kp = self._get_or_create_kp(provider,
                                    cloudlaunch_config.get('keyPair') or
                                    'cloudlaunch_key_pair')
        task.update_state(state='PROGRESSING',
                          meta={'action': "Applying firewall settings"})
        subnet_id, placement_zone, sgs = self.resolve_launch_properties(
            provider, cloudlaunch_config)
        cb_launch_config = self._get_cb_launch_config(provider, img,
                                                      cloudlaunch_config)
        inst_type = cloudlaunch_config.get(
            'instanceType', cloud_version_config.default_instance_type)

        log.debug("Launching with subnet %s and SGs %s" % (subnet_id, sgs))
        log.info("Launching base_vm with UD:\n%s" % user_data)
        task.update_state(state='PROGRESSING',
                          meta={'action': "Launching an instance of type %s "
                                "with keypair %s in zone %s" %
                                (inst_type, kp.name, placement_zone)})
        inst = provider.compute.instances.create(
            name=name, image=img, instance_type=inst_type, subnet=subnet_id,
            key_pair=kp, security_groups=sgs, zone=placement_zone,
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
        # FIXME: this does not account for multiple SGs and expects one
        results['securityGroup'] = {'id': sgs[0].id, 'name': sgs[0].name}
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
        return {'cloudLaunch': results}

    def _get_deployment_iid(self, deployment):
        """
        Extract instance ID for the supplied deployment.

        @type  deployment: ``ApplicationDeployment``
        @param deployment: An instance of the app deployment.

        :rtype: ``str``
        :return: Provider-specific instance ID for the deployment.
        """
        launch_task = deployment.tasks.filter(action='LAUNCH').first()
        return yaml.load(launch_task.result).get('cloudLaunch', {}).get(
            'instance', {}).get('id')

    def health_check(self, deployment, credentials):
        """Check the health of this app."""
        iid = self._get_deployment_iid(deployment)
        log.debug("Checking the status of instance %s", iid)
        provider = domain_model.get_cloud_provider(deployment.target_cloud,
                                                   credentials)
        inst = provider.compute.instances.get(iid)
        if inst:
            return {'instance_status': inst.state}
        else:
            return {'instance_status': 'terminated'}

    def delete(self, deployment, credentials):
        """
        Delete resource(s) associated with the supplied deployment.

        *Note* that this method will delete resource(s) associated with
        the deployment - this is un-recoverable action.
        """
        iid = self._get_deployment_iid(deployment)
        log.debug("Deleting deployment %s instance %s", (deployment.name, iid))
        provider = domain_model.get_cloud_provider(deployment.target_cloud,
                                                   credentials)
        inst = provider.compute.instances.get(iid)
        if inst:
            return inst.terminate()
        # Instance does not exist so default to True
        return True
