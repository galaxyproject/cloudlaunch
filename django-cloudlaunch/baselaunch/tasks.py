"""Tasks to be executed asynchronously (via Celery)."""
import copy
import json

from celery.app import shared_task
from celery.exceptions import Ignore
from celery.exceptions import SoftTimeLimitExceeded
from celery.result import AsyncResult
from celery.utils.log import get_task_logger

from baselaunch import domain_model
from baselaunch import models
from baselaunch import signals
from baselaunch import util

LOG = get_task_logger(__name__)


@shared_task
def migrate_launch_task(task_id):
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
        provider = domain_model.get_cloud_provider(cloud_version_config.cloud,
                                                   credentials)
        cloud_config = util.serialize_cloud_config(cloud_version_config)
        launch_result = handler.launch_app(provider, Task(launch_appliance),
                                           name, cloud_config, app_config,
                                           user_data)
        # Schedule a task to migrate result one hour from now
        migrate_launch_task.apply_async([launch_appliance.request.id],
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
def migrate_task_result(task_id):
    """Migrate task results to the database from the broker table."""
    LOG.debug("Migrating task %s result to the DB" % task_id)
    adt = models.ApplicationDeploymentTask.objects.get(celery_id=task_id)
    task = AsyncResult(task_id)
    task_meta = task.backend.get_task_meta(task.id)
    adt.celery_id = None
    adt.status = task_meta.get('status')
    adt.result = json.dumps(task_meta.get('result'))
    adt.traceback = task_meta.get('traceback')
    adt.save()
    task.forget()


def _serialize_deployment(deployment):
    """
    Extract appliance info for the supplied deployment and serialize it.

    @type  deployment: ``ApplicationDeployment``
    @param deployment: An instance of the app deployment.

    :rtype: ``str``
    :return: Serialized info about the appliance deployment, which corresponds
             to the result of the LAUNCH task.
    """
    launch_task = deployment.tasks.filter(
        action=models.ApplicationDeploymentTask.LAUNCH).first()
    if launch_task:
        return {'launch_status': launch_task.status,
                'launch_result': launch_task.result}
    else:
        return {'launch_status': None, 'launch_result': {}}


@shared_task(bind=True)
def health_check(self, deployment, credentials):
    """
    Check the health of the supplied deployment.

    Conceptually, the health check can be as elaborate as the deployed
    appliance supports via a custom implementation. At the minimum, and
    by default, the health reflects the status of the cloud instance by
    querying the cloud provider.
    """
    LOG.debug("Checking health of deployment %s", deployment.name)
    handler = _get_app_handler(deployment)
    dpl = _serialize_deployment(deployment)
    provider = domain_model.get_cloud_provider(deployment.target_cloud,
                                               credentials)
    result = handler.health_check(provider, dpl)
    # We only keep the two most recent health check task results so delete
    # any older ones
    signals.health_check.send(sender=None, deployment=deployment)
    # Schedule a task to migrate results right after task completion
    # Do this as a separate task because until this task completes, we
    # cannot obtain final status or traceback.
    migrate_task_result.apply_async([self.request.id], countdown=1)
    return result


@shared_task(bind=True)
def manage_appliance(self, action, deployment, credentials):
    """
    Perform supplied action on this app.

    @type action: ``str``
    @param action: Accepted values are ``restart`` or ``delete``.
    """
    LOG.debug("Performing %s on deployment %s", action, deployment.name)
    handler = _get_app_handler(deployment)
    dpl = _serialize_deployment(deployment)
    provider = domain_model.get_cloud_provider(deployment.target_cloud,
                                               credentials)
    if action.lower() == 'restart':
        result = handler.restart(provider, dpl)
    elif action.lower() == 'delete':
        result = handler.delete(provider, dpl)
    else:
        LOG.error("Unrecognized action: %s. Acceptable values are 'delete' "
                  "or 'restart'", action)
        return None
    # Schedule a task to migrate results right after task completion
    # Do this as a separate task because until this task completes, we
    # cannot obtain final status or traceback.
    migrate_task_result.apply_async([self.request.id],
                                    countdown=1)
    return result


class Task(object):
    """
    An abstraction class for handling task actions.

    Plugins can implement the interface defined here and handle task actions
    independent CloudLaunch and its task broker.
    """

    def __init__(self, broker_task):
        self.task = broker_task

    def update_state(self, task_id=None, state=None, meta=None):
        """
        Update task state.

        @type  task_id: ``str``
        @param task_id: Id of the task to update. Defaults to the id of the
                        current task.

        @type  state: ``str
        @param state: New state.

        @type  meta: ``dict``
        @param meta: State meta-data.
        """
        self.task.update_state(state=state, meta=meta)
