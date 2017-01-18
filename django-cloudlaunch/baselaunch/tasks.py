"""Tasks to be executed asynchronously (via Celery)."""
from baselaunch import util
from celery.app import shared_task


@shared_task
def launch_appliance(name, cloud_version_config, credentials, app_config,
                     user_data, task_id=None):
    """Call the appropriate app handler and initiate the app launch process."""
    handler = util.import_class(
        cloud_version_config.application_version.backend_component_name)()
    return handler.launch_app(launch_appliance, name, cloud_version_config,
                              credentials, app_config, user_data)
