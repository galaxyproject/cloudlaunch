import yaml
from baselaunch import util
from celery.app import shared_task


@shared_task
def launch_appliance(name, cloud_version_config, credentials, app_config, user_data):
    handler = util.import_class(cloud_version_config.application_version.backend_component_name)()
    return handler.launch_app(name, cloud_version_config, credentials, app_config, user_data)
