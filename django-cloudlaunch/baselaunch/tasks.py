import yaml
from baselaunch import util
from celery.app import shared_task


@shared_task
def launch_appliance(credentials, cloud, version, cloud_version_config, app_config, user_data):
    handler = util.import_class(version.backend_component_name)()
    return handler.launch_app(credentials, cloud, version, cloud_version_config, app_config, user_data)
