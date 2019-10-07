import yaml
from rest_framework.serializers import ValidationError
from .cloudman_app import CloudManAppPlugin
from .base_vm_app import BaseVMAppPlugin


class DockerAppPlugin(BaseVMAppPlugin):

    @staticmethod
    def validate_app_config(provider, name, cloud_config, app_config):
        docker_config = app_config.get('config_docker')
        if not docker_config:
            raise ValidationError("Docker configuration data must be provided.")
        docker_file_config = {} if not docker_config.get('docker_file') else docker_config['docker_file']
        config_cloudlaunch = app_config.get('config_cloudlaunch')
        firewall_config = config_cloudlaunch.get('firewall', [])
        if firewall_config:
            security_group = firewall_config[0]
            security_rules = security_group.get('rules', [])
        else:
            security_rules = []
            security_group = {'securityGroup': 'cloudlaunch_docker',
                              'description': 'Security group for docker containers',
                              'rules': security_rules}
            firewall_config.append(security_group)
        user_data = "#!/bin/bash\ndocker run -d"
        for mapping in docker_file_config.get('port_mappings', {}):
            host_port = mapping.get('host_port')
            if host_port:
                user_data += " -p {0}:{1}".format(host_port, mapping.get('container_port'))
                security_rules.append(
                    {
                        'protocol': 'tcp',
                        'from': host_port,
                        'to': host_port,
                        'cidr': '0.0.0.0/0' })
        security_group['rules'] = security_rules
        config_cloudlaunch['firewall'] = firewall_config
        
        for envvar in docker_file_config.get('env_vars', {}):
            envvar_name = envvar.get('variable')
            if envvar_name:
                user_data += " -e \"{0}={1}\"".format(envvar_name, envvar.get('value'))

        for vol in docker_file_config.get('volumes', {}):
            container_path = vol.get('container_path')
            if container_path:
                user_data += " -v {0}:{1}:{2}".format(vol.get('host_path'),
                                                      container_path,
                                                      'rw' if vol.get('read_write') else 'r')

        user_data += " {0}".format(docker_config.get('repo_name'))
        return user_data

    def deploy(self, name, task, app_config, provider_config):
        result = super(DockerAppPlugin, self).deploy(
            name, task, app_config, provider_config)
        result['cloudLaunch']['applicationURL'] = 'http://{0}'.format(
            result['cloudLaunch']['hostname'])
        return result
