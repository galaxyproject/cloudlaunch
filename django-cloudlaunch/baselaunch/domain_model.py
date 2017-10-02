"""
Represents the domain model and provides a higher level abstraction over the
base model. This layer is separate from the view in that it does not deal
with requests directly and only with model objects - thus making it
reusable without a related web request.
"""
from cloudbridge.cloud.factory import CloudProviderFactory, ProviderList

from baselaunch import models


def get_cloud_provider(cloud, cred_dict):
    """
    Returns a provider for a cloud given a cloud model and a dictionary
    containing the relevant credentials.

    :type cloud: Cloud
    :param cloud: The cloud to create a provider for

    :rtype: ``object`` of :class:`.dict`
    :return:  A dict containing the necessary credentials for the cloud.
    """
    # In case a base class instance is sent in, attempt to retrieve the actual
    # subclass.
    if type(cloud) is models.Cloud:
        cloud = models.Cloud.objects.get_subclass(slug=cloud.slug)

    if isinstance(cloud, models.OpenStack):
        config = {'os_auth_url': cloud.auth_url,
                  'os_region_name': cloud.region_name}
        config.update(cred_dict)
        return CloudProviderFactory().create_provider(ProviderList.OPENSTACK,
                                                      config)
    elif isinstance(cloud, models.AWS):
        config = {'ec2_is_secure': cloud.compute.ec2_is_secure,
                  'ec2_region_name': cloud.compute.ec2_region_name,
                  'ec2_region_endpoint': cloud.compute.ec2_region_endpoint,
                  'ec2_port': cloud.compute.ec2_port,
                  'ec2_conn_path': cloud.compute.ec2_conn_path,
                  's3_host': cloud.object_store.s3_host,
                  's3_port': cloud.object_store.s3_port,
                  's3_conn_path': cloud.object_store.s3_conn_path}
        config.update(cred_dict)
        return CloudProviderFactory().create_provider(ProviderList.AWS,
                                                      config)
    elif isinstance(cloud, models.Azure):
        config = {'azure_region_name': cloud.region_name,
                  'azure_resource_group': cloud.resource_group,
                  'azure_storage_account': cloud.storage_account,
                  'azure_vm_default_user_name': cloud.vm_default_user_name}
        config.update(cred_dict)
        return CloudProviderFactory().create_provider(ProviderList.AZURE,
                                                      config)
    elif isinstance(cloud, models.GCE):
        config = {'gce_service_creds_dict': cred_dict,
                  'gce_default_zone': cloud.zone_name,
                  'gce_region_name': cloud.region_name}
        return CloudProviderFactory().create_provider(ProviderList.GCE,
                                                      config)
    else:
        raise Exception("Unrecognised cloud provider: %s" % cloud)
