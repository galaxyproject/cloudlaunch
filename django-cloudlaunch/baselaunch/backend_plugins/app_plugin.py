import abc
import yaml

from baselaunch import domain_model


class BaseAppPlugin():

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
            return provider.security.security_groups.create(name=sg_name,
                                                            description=description)

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
        cloudlaunch_config = app_config.get("config_cloudlaunch", {})
        provider = domain_model.get_cloud_provider(cloud_version_config.cloud, credentials)
        img = provider.compute.images.get(cloud_version_config.image.image_id)
        kp = self._get_or_create_kp(provider, cloudlaunch_config.get('keyPair') or 'cloudlaunch_key_pair')
        sg = self.apply_app_firewall_settings(
            provider, cloudlaunch_config.get('firewall', []))

        inst_type = cloudlaunch_config.get(
            'instanceType', cloud_version_config.default_instance_type)
        placement_zone = cloudlaunch_config.get('placementZone')
        
        ud = yaml.dump(user_data, default_flow_style=False, allow_unicode=False)
        print("Launching with ud: %s" % (ud,))
        print("Launching an instance of type %s with KP %s in zone %s" % (inst_type, kp, placement_zone))
        inst = provider.compute.instances.create(name=name, image=img,
            instance_type=inst_type, key_pair=kp, security_groups=[sg],
            zone = placement_zone, user_data=ud)
        print("Launched instance with ID: %s" % inst.id)
        result = {}
        result['keyPair'] = { 'id' : kp.id, 'name' : kp.name, 'material' : kp.material }
        results['securityGroup'] = {'id' : sg.id, 'name' : sg.name }
        results['publicIP'] = inst.public_ips[0]
        return {'cloudLaunch' : results }
