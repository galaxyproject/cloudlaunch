"""Tasks to be executed asynchronously (via Celery)."""
import copy
import json

from celery.app import shared_task
from celery.exceptions import Ignore
from celery.exceptions import SoftTimeLimitExceeded
from celery.result import AsyncResult
from celery.utils.log import get_task_logger

from baselaunch import models
from baselaunch import util

LOG = get_task_logger(__name__)


@shared_task
def migrate_task_result(task_id):
    """
    Migrate task result to a persistent model table.

    Task result may contain temporary info that we don't want to keep. This
    task is intended to be called some time after the initial task has run to
    migrate the info we do want to keep to a model table.
    """
    adt = models.ApplicationDeploymentTask.objects.get(celery_id=task_id)
    task = AsyncResult(task_id)
    task_meta = task.backend.get_task_meta(task.id)
    adt.status = task_meta.get('status')
    adt.traceback = task_meta.get('traceback')
    adt.celery_id = None
    sanitized_result = copy.deepcopy(task_meta['result'])
    if sanitized_result.get('cloudLaunch', {}).get('keyPair', {}).get(
            'material'):
        sanitized_result['cloudLaunch']['keyPair']['material'] = None
    adt.result = json.dumps(sanitized_result)
    adt.save()
    task.forget()


@shared_task
def launch_appliance(name, cloud_version_config, credentials, app_config,
                     user_data, task_id=None):
    """Call the appropriate app handler and initiate the app launch process."""
    try:
        LOG.debug("Launching appliance %s", name)
        handler = util.import_class(
            cloud_version_config.application_version.backend_component_name)()
        launch_result = handler.launch_app(launch_appliance, name,
                                           cloud_version_config, credentials,
                                           app_config, user_data)
        # Schedule a task to migrate result one hour from now
        migrate_task_result.apply_async([launch_appliance.request.id],
                                        countdown=3600)
        return launch_result
    except SoftTimeLimitExceeded:
        launch_appliance.update_state(
            state="FAILURE", meta={"exc_message": "Task time limit exceeded; "
                                                  "stopping the task."})
        raise Ignore  # This keeps the custom state set above


def _get_app_handler(deployment):
    """
    Retrieve app-specific handler for a deployment.

    :rtype: :class:`.AppPlugin`
    :return: An instance of the handler class corresponding to the
             deployment app.
    """
    cloud = deployment.target_cloud
    cloud_version_config = models.ApplicationVersionCloudConfig.objects.get(
        application_version=deployment.application_version.id, cloud=cloud.slug)
    return util.import_class(
        cloud_version_config.application_version.backend_component_name)()


@shared_task
def health_check(deployment, credentials):
    """
    Check the health of the supplied deployment.

    Conceptually, the health check can be as elaborate as the deployed
    appliance supports via a custom implementation. At the minimum, and
    by default, the health reflects the status of the cloud instance by
    querying the cloud provider.
    """
    LOG.debug("Checking health of deployment %s", deployment.name)
    handler = _get_app_handler(deployment)
    return handler.health_check(deployment, credentials)


@shared_task
def delete_appliance(deployment, credentials):
    """Delete this app. This is an un-recoverable action."""
    LOG.debug("Deleting deployment %s", deployment.name)
    handler = _get_app_handler(deployment)
    return handler.delete(deployment, credentials)
