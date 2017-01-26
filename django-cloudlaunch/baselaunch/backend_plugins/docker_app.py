import yaml
from rest_framework.serializers import ValidationError
from .cloudman_app import CloudManAppPlugin
from .base_vm_app import BaseVMAppPlugin


class DockerAppPlugin(BaseVMAppPlugin):

    @staticmethod
    def process_app_config(name, cloud_version_config, credentials, app_config):
        docker_config = app_config.get('config_docker')
        config_cloudlaunch = app_config.get('config_cloudlaunch')
        firewall_config = config_cloudlaunch.get('firewall', [])
        if firewall_config:
            security_group = firewall_config[0]
            security_rules = security_group.get('rules', [])
        else:
            security_rules = []
            security_group = { securityGroup: 'cloudlaunch_docker',
                              description: 'Security group for docker containers',
                              rules: security_rules }
            firewall_config.append(security_group)
        if not docker_config:
            raise ValidationError("Docker configuration data must be provided.")
        user_data = "#!/bin/bash\ndocker run -d"
        for mapping in docker_config.get('port_mappings', {}):
            host_port = mapping.get('host_port')
            if host_port:
                user_data += " -p {0}:{1}".format(mapping.get('container_port'), host_port)
                security_rules.append(
                    {
                        'protocol': 'tcp',
                        'from': host_port,
                        'to': host_port,
                        'cidr': '0.0.0.0/0' })
        security_group['rules'] = security_rules
        config_cloudlaunch['firewall'] = firewall_config
        user_data += " {0}".format(docker_config.get('repo_name'))
        
        return user_data

    def launch_app(self, task, name, cloud_version_config, credentials, app_config, user_data):
        result = super(DockerAppPlugin, self).launch_app(task, name, cloud_version_config, credentials, app_config, user_data)
        result['cloudLaunch']['applicationURL'] = 'http://{0}'.format(result['cloudLaunch']['publicIP'])
        return result
