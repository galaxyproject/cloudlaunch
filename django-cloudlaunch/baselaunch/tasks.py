import yaml
from baselaunch import util


def launch_appliance(credentials, cloud, version, cloud_version_config, cloudlaunch_config, user_data):
    handler = util.import_class(version.backend_component_name)()
    handler.launch_app(credentials, cloud, version, cloud_version_config, cloudlaunch_config, user_data)
    return "dummy-task-id"
