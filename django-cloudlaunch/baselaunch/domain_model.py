from cloudbridge.cloud.factory import CloudProviderFactory, ProviderList

from baselaunch import models


def get_cloud_provider(cloud_pk, request):
    cloud = models.Cloud.objects.filter(
        slug=cloud_pk).select_subclasses().first()
    profile = request.user.userprofile
    credentials = profile.credentials_set.filter(cloud=cloud). \
        select_subclasses().first()
    if isinstance(cloud, models.OpenStack):
        config = {'os_auth_url': cloud.auth_url,
                  'os_region_name': cloud.region_name,
                  'os_username': credentials.username,
                  'os_password': credentials.password,
                  'os_tenant_name': credentials.tenant_name
                  }
        return CloudProviderFactory().create_provider(ProviderList.OPENSTACK,
                                                      config)
    elif isinstance(cloud, models.AWS):
        config = {'ec2_is_secure': cloud.compute.ec2_is_secure,
                  'ec2_region_name': cloud.compute.ec2_region_name,
                  'ec2_region_endpoint': cloud.compute.ec2_region_endpoint,
                  'ec2_port': cloud.compute.ec2_port,
                  'ec2_conn_path': cloud.compute.ec2_conn_path,
                  'aws_access_key': credentials.access_key,
                  'aws_secret_key': credentials.secret_key,
                  }
        return CloudProviderFactory().create_provider(ProviderList.AWS,
                                                      config)
    else:
        raise Exception("Unrecognised cloud provider: %s" % cloud)
