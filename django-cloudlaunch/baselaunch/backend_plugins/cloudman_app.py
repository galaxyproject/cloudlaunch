from rest_framework.serializers import ValidationError
from .app_plugin import BaseAppPlugin


def get_required_val(data, name, message):
    val = data.get(name)
    if not val:
        raise ValidationError(message)
    return val


class CloudManConfigHandler(BaseAppPlugin):

    @staticmethod
    def process_config_data(cloud_version_config, data):
        cloudman_config = get_required_val(
            data, "config_cloudman", "CloudMan configuration data must be provided.")
        user_data = {}
        user_data['bucket_default'] = get_required_val(
            cloudman_config, "defaultBucket", "default bucket is required.")
        user_data['cluster_name'] = get_required_val(
            cloudman_config, "clusterName", "cluster name is required.")
        user_data['password'] = get_required_val(
            cloudman_config, "clusterPassword", "cluster name is required.")
        user_data['initial_cluster_type'] = get_required_val(
            cloudman_config, "clusterType", "cluster type is required.")
        user_data['storageType'] = get_required_val(
            cloudman_config, "storageType", "storage type is required.")
        user_data['storage_size'] = cloudman_config.get("storageSize")
        user_data['post_start_script_url'] = cloudman_config.get(
            "masterPostStartScript")
        user_data['worker_post_start_script_url'] = cloudman_config.get(
            "workerPostStartScript")
        user_data['share_string'] = cloudman_config.get("clusterSharedString")
        user_data['cluster_templates'] = cloudman_config.get(
            "cluster_templates")

        cloud = cloud_version_config.cloud
        if hasattr(cloud, 'aws'):
            user_data['cloud_type'] = 'ec2'
            user_data['region_name'] = cloud.aws.compute.ec2_region_name
            user_data['region_endpoint'] = cloud.aws.compute.ec2_region_endpoint
            user_data['ec2_conn_path'] = cloud.aws.compute.ec2_conn_path
            user_data['ec2_is_secure'] = cloud.aws.compute.ec2_is_secure
            user_data['ec2_port'] = cloud.aws.compute.ec2_port
            user_data['s3_conn_path'] = cloud.aws.object_store.s3_conn_path
            user_data['s3_host'] = cloud.aws.object_store.s3_host
            user_data['s3_port'] = cloud.aws.object_store.s3_port
        else:
            raise ValidationError(
                "This version of CloudMan supports only EC2 based clouds.")

        return user_data

