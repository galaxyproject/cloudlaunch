from .app_plugin import AppPlugin
from baselaunch import domain_model
import requests
import time


class BaseVMAppPlugin(AppPlugin):


    @staticmethod
    def process_app_config(name, cloud_version_config, credentials, app_config):
        return app_config.get("config_cloudlaunch", {}).get("instance_user_data", {})

    def _get_or_create_kp(self, provider, kp_name):
        """
        If a keypair with the provided ``kp_name`` does not exist, create it.
        """
        kps = provider.security.key_pairs.find(name=kp_name)
        if kps:
            return kps[0]
        else:
            return provider.security.key_pairs.create(name=kp_name)

    def _get_or_create_sg(self, provider, cloudlaunch_config, sg_name,
                          description):
        """Fetch an existing security group named ``sg_name`` or create one."""
        network_id = self._get_network_id(provider, cloudlaunch_config)
        sgs = provider.security.security_groups.find(name=sg_name)
        for sg1 in sgs:
            for sg2 in sgs:
                if sg1 == sg2:
                    return sg1
        return provider.security.security_groups.create(
            name=sg_name, description=description, network_id=network_id)

    def _get_cb_launch_config(self, provider, image, cloudlaunch_config):
        """
        Compose a CloudBridge launch config object.
        """
        network_id = self._get_network_id(provider, cloudlaunch_config)
        lc = None
        if network_id:
            lc = provider.compute.instances.create_launch_config()
            lc.add_network_interface(network_id)
        if cloudlaunch_config.get("rootStorageType", "instance") == "volume":
            if not lc:
                lc = provider.compute.instances.create_launch_config()
            lc.add_volume_device(source=image,
                                 size=int(cloudlaunch_config.get("rootStorageSize", 20)),
                                 is_root=True)

        return lc

    def _get_network_id(self, provider, cloudlaunch_config):
        """
        Figure out the IDs of relevant networks.

        Return a dictionary with ``network_id`` and ``subnet_id`` keys.
        Values for the networks come from ``cloudlaunch_config`` field, as
        supplied in the request. For the AWS case, if not network is supplied,
        the default VPC is used.
        """
        return cloudlaunch_config.get('network', None)

    def apply_app_firewall_settings(self, provider, cloudlaunch_config):
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
        for group in cloudlaunch_config.get('firewall', []):
            sg_name = group.get('securityGroup') or 'CloudLaunchDefault'
            sg_desc = group.get('description') or 'Created by CloudLaunch'
            sg = self._get_or_create_sg(provider, cloudlaunch_config, sg_name, sg_desc)
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

    def wait_for_http(self, url, max_retries=200,
                 poll_interval=5):
        """Wait till app is responding at http URL"""
        count = 0
        while time.sleep(poll_interval) and count < max_retries:
            try:
                r = requests.head(url)
                r.raise_for_status()
                return
            except requests.exception.HTTPError as e:
                if e.response.status_code in (200, 401, 403):
                    return
            count += 1


    def launch_app(self, task, name, cloud_version_config, credentials, app_config, user_data):
        cloudlaunch_config = app_config.get("config_cloudlaunch", {})
        provider = domain_model.get_cloud_provider(cloud_version_config.cloud, credentials)
        img = provider.compute.images.get(cloud_version_config.image.image_id)
        task.update_state(state='PROGRESSING', meta={'action': "Retrieving or creating a keypair"})
        kp = self._get_or_create_kp(provider, cloudlaunch_config.get('keyPair') or 'cloudlaunch_key_pair')
        task.update_state(state='PROGRESSING', meta={'action': "Applying firewall settings"})
        sg = self.apply_app_firewall_settings(
            provider, cloudlaunch_config)
        cb_launch_config = self._get_cb_launch_config(provider, img, cloudlaunch_config)
        inst_type = cloudlaunch_config.get(
            'instanceType', cloud_version_config.default_instance_type)
        placement_zone = cloudlaunch_config.get('placementZone')

        print("Launching with ud:\n%s" % user_data)
        task.update_state(state='PROGRESSING', meta={'action': "Launching an instance of type %s with keypair %s in zone %s" %
              (inst_type, kp.name, placement_zone)})
        inst = provider.compute.instances.create(name=name, image=img,
            instance_type=inst_type, key_pair=kp, security_groups=[sg],
            zone = placement_zone, user_data=user_data, launch_config=cb_launch_config)
        task.update_state(state='PROGRESSING', meta={'action': "Waiting for instance %s to be ready.." % (inst.id, )})
        inst.wait_till_ready()
        static_ip = cloudlaunch_config.get('staticIP')
        if static_ip:
            task.update_state(state='PROGRESSING', meta={'action': "Assigning requested static IP: %s" % (static_ip, )})
            inst.add_floating_ip(static_ip)
            inst.refresh()
        results = {}
        results['keyPair'] = { 'id' : kp.id, 'name' : kp.name, 'material' : kp.material }
        results['securityGroup'] = {'id' : sg.id, 'name' : sg.name }
        results['publicIP'] = inst.public_ips[0] if len(inst.public_ips) > 0 else None
        task.update_state(
            state='PROGRESSING',
            meta={'action': "VM creation successful. Public IP (if available): %s"
                  % results['publicIP']})
        results['applicationURL'] = '{0}'.format(results['publicIP'])
        task.update_state(
            state='PROGRESSING',
            meta={'action': "Waiting for application to become ready at: %s"
                  % results['applicationURL']})
        self.wait_for_http(results['applicationURL'])
        return {'cloudLaunch' : results }
