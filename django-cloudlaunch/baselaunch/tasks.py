import yaml

def _get_or_create_key_pair(provider, kp_name):
    """
    If a key pair with the provided ``kp_name`` does not exist, create it.
    """
    kp = provider.security.key_pairs.find(name=kp_name)
    if kp:
        kp = kp[0]
    else:
        kp = provider.security.key_pairs.create(name=kp_name)
    return kp

def launch_appliance(provider, cloud_version_config, launch_config, user_data):
    kp = _get_or_create_key_pair(provider, launch_config.get(
        'keyPair', 'cloudman_key_pair'))
    sg = provider.security.security_groups.find('CloudMan')[0]
    img = provider.compute.images.get(cloud_version_config.image.image_id)
    it = launch_config.get(
        'instanceType', cloud_version_config.default_instance_type)
    inst_type = provider.compute.instance_types.get(it)
    if hasattr(cloud_version_config.cloud, 'aws'):
        user_data['cloud_type'] = 'ec2'
        user_data['region_name'] = \
            cloud_version_config.cloud.aws.compute.ec2_region_name
        user_data['region_endpoint'] = \
            cloud_version_config.cloud.aws.compute.ec2_region_endpoint
        user_data['ec2_conn_path'] = \
            cloud_version_config.cloud.aws.compute.ec2_conn_path
        user_data['ec2_is_secure'] = \
            cloud_version_config.cloud.aws.compute.ec2_is_secure
        user_data['ec2_port'] = \
            cloud_version_config.cloud.aws.compute.ec2_port
        user_data['s3_conn_path'] = \
            cloud_version_config.cloud.aws.object_store.s3_conn_path
        user_data['s3_host'] = \
            cloud_version_config.cloud.aws.object_store.s3_host
        user_data['s3_port'] = \
            cloud_version_config.cloud.aws.object_store.s3_port
    elif hasattr(cloud_version_config.cloud, 'openstack'):
        user_data['cloud_type'] = 'openstack'
        # TODO: CloudMan will not recognize non-EC2/boto connection params so
        # composing native OpenStack connection info will have to wait
    else:
        print("Cloud not recognized; region endpoint missing.")
    ud = yaml.dump(user_data, default_flow_style=False, allow_unicode=False)
    print("Launching an instance type %s, KP %s, with ud: %s" %
          (inst_type, kp, ud))
    # # inst = provider.compute.instances.create(
    # #     name=launch_data.get('cluster_name'), image=img,
    # #     instance_type=inst_type, key_pair=kp, security_groups=[sg],
    # #     user_data=ud)
    # print("Launched instance with ID: %s" % inst.id)
    return "dummy-task-id"
