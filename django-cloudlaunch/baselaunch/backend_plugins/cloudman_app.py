import yaml
from urllib.parse import urlparse
from rest_framework.serializers import ValidationError
from .base_vm_app import BaseVMAppPlugin
from baselaunch import domain_model


def get_required_val(data, name, message):
    val = data.get(name)
    if not val:
        raise ValidationError({ "error" : message })
    return val


class CloudManAppPlugin(BaseVMAppPlugin):

    @staticmethod
    def process_app_config(name, cloud_version_config, credentials, app_config):
        cloudman_config = get_required_val(
            app_config, "config_cloudman", "CloudMan configuration data must be provided.")
        user_data = {}
        user_data['bucket_default'] = get_required_val(
            cloudman_config, "defaultBucket", "default bucket is required.")
        user_data['cluster_name'] = name
        user_data['password'] = get_required_val(
            cloudman_config, "clusterPassword", "cluster name is required.")
        user_data['initial_cluster_type'] = get_required_val(
            cloudman_config, "clusterType", "cluster type is required.")
        user_data['cluster_storage_type'] = get_required_val(
            cloudman_config, "storageType", "storage type is required.")
        user_data['storage_size'] = cloudman_config.get("storageSize")
        user_data['post_start_script_url'] = cloudman_config.get(
            "masterPostStartScript")
        user_data['worker_post_start_script_url'] = cloudman_config.get(
            "workerPostStartScript")
        if cloudman_config.get("clusterSharedString"):
            user_data['share_string'] = cloudman_config.get("clusterSharedString")
        user_data['cluster_templates'] = cloudman_config.get(
            "cluster_templates")

        cloud = cloud_version_config.cloud
        if hasattr(cloud, 'aws'):
            user_data['cloud_type'] = 'ec2'
            user_data['region_name'] = cloud.aws.compute.ec2_region_name
            user_data['region_endpoint'] = cloud.aws.compute.ec2_region_endpoint
            user_data['ec2_port'] = cloud.aws.compute.ec2_port
            user_data['ec2_conn_path'] = cloud.aws.compute.ec2_conn_path
            user_data['is_secure'] = cloud.aws.compute.ec2_is_secure
            user_data['s3_host'] = cloud.aws.object_store.s3_host
            user_data['s3_port'] = cloud.aws.object_store.s3_port
            user_data['s3_conn_path'] = cloud.aws.object_store.s3_conn_path
            user_data['access_key'] = credentials.get('aws_access_key')
            user_data['secret_key'] = credentials.get('aws_secret_key')
        elif hasattr(cloud, 'openstack'):
            user_data['cloud_type'] = 'openstack'
            provider = domain_model.get_cloud_provider(cloud_version_config.cloud, credentials)
            ec2_endpoints = provider.security.get_ec2_endpoints()
            if not ec2_endpoints.get('ec2_endpoint'):
                raise ValidationError({ "error":
                "This version of CloudMan supports only EC2-compatible clouds. This OpenStack"
                " cloud provider does not appear to have an ec2 endpoint"})
            uri_comp = urlparse(ec2_endpoints.get('ec2_endpoint'))

            user_data['region_name'] = cloud.openstack.region_name
            user_data['region_endpoint'] = uri_comp.hostname
            user_data['ec2_port'] = uri_comp.port
            user_data['ec2_conn_path'] = uri_comp.path
            user_data['is_secure'] = uri_comp.scheme == "https"

            if ec2_endpoints.get('s3_endpoint'):
                uri_comp = urlparse(ec2_endpoints.get('s3_endpoint'))
                user_data['s3_host'] = uri_comp.hostname
                user_data['s3_port'] = uri_comp.port
                user_data['s3_conn_path'] = uri_comp.path
            else:
                user_data['use_object_store'] = False

            ec2_creds = provider.security.get_ec2_credentials()
            user_data['access_key'] = ec2_creds.access
            user_data['secret_key'] = ec2_creds.secret
        else:
            raise ValidationError({ "error":
                "This version of CloudMan supports only EC2-compatible clouds."})

        return user_data
    
    @staticmethod
    def sanitise_app_config(app_config):
        app_config = super(CloudManAppPlugin, CloudManAppPlugin).sanitise_app_config(app_config)
        app_config['config_cloudman']['clusterPassword'] = '********'
        return app_config

    def launch_app(self, task, name, cloud_version_config, credentials, app_config, user_data):
        print("YAML UD:\n%s" % user_data)
        ud = yaml.dump(user_data, default_flow_style=False, allow_unicode=False)
        result = super(CloudManAppPlugin, self).launch_app(task, name, cloud_version_config, credentials, app_config, ud)
        result['cloudLaunch']['applicationURL'] = 'http://{0}'.format(result['cloudLaunch']['publicIP'])
        return result
