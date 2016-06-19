import abc
import yaml

from baselaunch import domain_model


class BaseAppPlugin():

    @abc.abstractstaticmethod
    def process_config_data(credentials, cloud_version_config, data):
        pass

    def _get_or_create_key_sg(self, provider, sg_name, description):
        """
        If a key pair with the provided ``kp_name`` does not exist, create it.
        """
        sg = provider.security.security_groups.find(name=sg_name)
        if sg:
            return sg[0]
        else:
            return provider.security.security_groups.create(name=sg_name,
                                                            description=description)

    def apply_app_firewall_settings(self, provider, firewall_settings):
        """
        Apply any firewall settings defined for the app in cloudlaunch
        settings. The following format is expected:

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
                "securityGroup": "CloudMan"
            }
        ]
        """
        for group in firewall_settings:
            sg_name = group.get('securityGroup') or 'CloudLaunchDefault'
            sg_desc = group.get('description') or 'Created by CloudLaunch'
            sg = self._get_or_create_key_sg(provider, sg_name, sg_desc)
            for rule in group.get('rules', []):
                sg.add_rule(ip_protocol=rule.get('protocol'),
                            from_port=rule.get('from'),
                            to_port=rule.get('to'),
                            cidr_ip=rule.get('cidr'))
                            #src_group=rule.get('src_group'))

    def launch_app(self, credentials, cloud, version,
                   cloud_version_config, app_config, user_data):
        cloudlaunch_config = app_config.get("config_cloudlaunch", {})
        provider = domain_model.get_cloud_provider(cloud, credentials)
        img = provider.compute.images.get(cloud_version_config.image.image_id)
        kp = provider.security.key_pairs.create(
            name=cloudlaunch_config.get('keyPair') or 'cloudlaunch_key_pair')
        self.apply_app_firewall_settings(provider, cloudlaunch_config.get('firewall', []))

        it = cloudlaunch_config.get(
            'instanceType', cloud_version_config.default_instance_type)
        inst_type = provider.compute.instance_types.get(it)

        ud = yaml.dump(user_data, default_flow_style=False, allow_unicode=False)
        print("Launching an instance type %s, KP %s, with ud: %s" %
              (inst_type, kp, ud))
        # # inst = provider.compute.instances.create(
        # #     name=launch_data.get('cluster_name'), image=img,
        # #     instance_type=inst_type, key_pair=kp, security_groups=[sg],
        # #     user_data=ud)
        # print("Launched instance with ID: %s" % inst.id)
