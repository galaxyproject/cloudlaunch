import json
from baselaunch import util
from baselaunch import models
from celery.app import shared_task


@shared_task
def launch_appliance(name, cloud_version_config, credentials, app_config, user_data, task_id=None):
    handler = util.import_class(cloud_version_config.application_version.backend_component_name)()
    result = handler.launch_app(launch_appliance, name, cloud_version_config, credentials, app_config, user_data)
    deployment = models.ApplicationDeployment.objects.get(celery_task_id=launch_appliance.request.id)
    deployment.task_result = json.dumps(result)
    deployment.save()
    return result
