import abc
import yaml

from baselaunch import domain_model


class BaseAppPlugin():
    def __init__(self, launch_config=None):
        self.cloudlaunch_config = launch_config

    @abc.abstractstaticmethod
    def process_app_config(name, cloud_version_config, credentials, app_config):
        pass

    def _get_or_create_kp(self, provider, kp_name):
        """
        If a keypair with the provided ``kp_name`` does not exist, create it.
        """
        kps = provider.security.key_pairs.find(name=kp_name)
        if kps:
            return kps[0]
        else:
            return provider.security.key_pairs.create(name=kp_name)

    def _get_or_create_sg(self, provider, sg_name, description):
        """
        If a security group with the provided ``sg_name`` does not exist, create it.
        """
        sgs = provider.security.security_groups.find(name=sg_name)
        if sgs:
            return sgs[0]
        else:
            network_id = self._get_networks(provider).get('network_id')
            return provider.security.security_groups.create(
                name=sg_name, description=description, network_id=network_id)

    def _get_cb_launch_config(self, provider):
        """
        Compose a CloudBridge launch config object.
        """
        networks = self._get_networks(provider)
        lc = None
        if networks.get('subnet_id'):
            lc = provider.compute.instances.create_launch_config()
            lc.add_network_interface(networks.get('subnet_id'))
        return lc

    def _get_networks(self, provider):
        """
        Figure out the IDs of relevant networks.

        Return a dictionary with ``network_id`` and ``subnet_id`` keys.
        Values for the networks come from ``cloudlaunch_config`` field, as
        supplied in the request. For the AWS case, if not network is supplied,
        the default VPC is used.
        """
        networks = {'network_id': None, 'subnet_id': None}
        if provider.cloud_type == 'aws':
            subnet_id = self.cloudlaunch_config.get('subnet', None)
            if subnet_id:
                networks['subnet_id'] = subnet_id
                sn = provider.network.subnets.get(subnet_id)
                networks['network_id'] = sn.network_id
            else:
                # User did not specify a network so find the default one
                for n in provider.network.list():
                    if n._vpc.is_default:
                        networks['network_id'] = n.id
        elif provider.cloud_type == 'openstack':
            networks['network_id'] = self.cloudlaunch_config.get('network', None)
        return networks

    def apply_app_firewall_settings(self, provider, firewall_settings):
        """
        Apply any firewall settings defined for the app in cloudlaunch
        settings and return the encompassing security group.

        The following format is expected:

        "firewall": [
            {
                "rules": [
                    {
                        "from": "1",
                        "to": "65535",
                        "src_group": "CloudMan",
                        "cidr": "0.0.0.0/0",
                        "protocol": "tcp"
                    }
                ],
                "securityGroup": "MyApp",
                "description": "My App SG"
            }
        ]
        """
        for group in firewall_settings:
            sg_name = group.get('securityGroup') or 'CloudLaunchDefault'
            sg_desc = group.get('description') or 'Created by CloudLaunch'
            sg = self._get_or_create_sg(provider, sg_name, sg_desc)
            for rule in group.get('rules', []):
                try:
                    sg.add_rule(ip_protocol=rule.get('protocol'),
                                from_port=rule.get('from'),
                                to_port=rule.get('to'),
                                cidr_ip=rule.get('cidr'),
                                src_group=rule.get('src_group'))
                except Exception as e:
                    print(e)
                    pass
            return sg

    def launch_app(self, name, cloud_version_config, credentials, app_config, user_data):
        self.cloudlaunch_config = app_config.get("config_cloudlaunch", {})
        provider = domain_model.get_cloud_provider(cloud_version_config.cloud, credentials)
        img = provider.compute.images.get(cloud_version_config.image.image_id)
        kp = self._get_or_create_kp(provider, self.cloudlaunch_config.get('keyPair') or 'cloudlaunch_key_pair')
        sg = self.apply_app_firewall_settings(
            provider, self.cloudlaunch_config.get('firewall', []))
        cb_launch_config = self._get_cb_launch_config(provider)
        inst_type = self.cloudlaunch_config.get(
            'instanceType', cloud_version_config.default_instance_type)
        placement_zone = self.cloudlaunch_config.get('placementZone')

        ud = yaml.dump(user_data, default_flow_style=False, allow_unicode=False)
        print("Launching with ud:\n%s" % (ud,))
        print("Launching an instance of type %s with KP %s in zone %s." %
              (inst_type, kp.name, placement_zone))
        inst = provider.compute.instances.create(name=name, image=img,
            instance_type=inst_type, key_pair=kp, security_groups=[sg],
            zone = placement_zone, user_data=ud, launch_config=cb_launch_config)
        print("Launched instance with ID: %s" % inst.id)
        results = {}
        results['keyPair'] = {'id': kp.id, 'name': kp.name, 'material': kp.material}
        results['securityGroup'] = {'id': sg.id, 'name': sg.name}
        results['publicIP'] = inst.public_ips[0]
        return {'cloudLaunch' : results }
