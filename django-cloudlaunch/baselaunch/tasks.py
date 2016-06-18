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
        'keyPair', 'cloudlaunch_key_pair'))
    sg = provider.security.security_groups.find('CloudMan')[0]
    img = provider.compute.images.get(cloud_version_config.image.image_id)
    it = launch_config.get(
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
    return "dummy-task-id"
