"""Tasks to be executed asynchronously (via Celery)."""
import copy
import json
import logging

from celery.app import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.result import AsyncResult
from celery.utils.log import get_task_logger

from djcloudbridge import domain_model
from . import models
from . import signals
from . import util

log = get_task_logger('cloudlaunch')
# Limit how much these libraries log
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('cloudbridge').setLevel(logging.INFO)


@shared_task(time_limit=120)
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


@shared_task(time_limit=120)
def update_status_task(task_id):
    """
    Update task result to a persistent model table.

    This task is intended to be called as soon as the launch task is over so
    we have a fairly up-to-date _status field in the model.
    """
    adt = models.ApplicationDeploymentTask.objects.get(celery_id=task_id)
    task = AsyncResult(task_id)
    task_meta = task.backend.get_task_meta(task.id)
    adt.status = task_meta.get('status')
    adt.save()


@shared_task(expires=120)
def create_appliance(name, cloud_version_config_id, credentials, app_config,
                     user_data):
    """Call the appropriate app plugin and initiate the app launch process."""
    try:
        log.debug("Creating appliance %s", name)
        cloud_version_conf = models.ApplicationVersionCloudConfig.objects.get(
            pk=cloud_version_config_id)
        plugin = util.import_class(
            cloud_version_conf.application_version.backend_component_name)()
        provider = domain_model.get_cloud_provider(
            cloud_version_conf.cloud, credentials)
        cloud_config = util.serialize_cloud_config(cloud_version_conf)
        # TODO: Add keys (& support) for using existing, user-supplied hosts
        provider_config = {'cloud_provider': provider,
                           'cloud_config': cloud_config,
                           'cloud_user_data': user_data}
        log.info("Provider_config: %s", provider_config)
        log.info("Creating app %s with the follwing app config: %s \n and "
                 "cloud config: %s", name, app_config, provider_config)
        deploy_result = plugin.deploy(name, Task(create_appliance), app_config,
                                      provider_config)
        # Upgrade task result immediately
        update_status_task.apply_async([create_appliance.request.id],
                                        countdown=1)
        # Schedule a task to migrate result one hour from now
        migrate_launch_task.apply_async([create_appliance.request.id],
                                        countdown=3600)
        return deploy_result
    except SoftTimeLimitExceeded:
        msg = "Create appliance task time limit exceeded; stopping the task."
        log.warning(msg)
        raise Exception(msg)
    except Exception as exc:
        msg = "Create appliance task failed: %s" % str(exc)
        log.error(msg)
        raise Exception(msg) from exc


def _get_app_plugin(deployment):
    """
    Retrieve appliance plugin for a deployment.

    :rtype: :class:`.AppPlugin`
    :return: An instance of the plugin class corresponding to the
             deployment app.
    """
    cloud = deployment.target_cloud
    cloud_version_config = models.ApplicationVersionCloudConfig.objects.get(
        application_version=deployment.application_version.id, cloud=cloud.slug)
    return util.import_class(
        cloud_version_config.application_version.backend_component_name)()


@shared_task(time_limit=120)
def migrate_task_result(task_id):
    """Migrate task results to the database from the broker table."""
    log.debug("Migrating task %s result to the DB" % task_id)
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


@shared_task(bind=True, time_limit=60, expires=300)
def health_check(self, deployment_id, credentials):
    """
    Check the health of the supplied deployment.

    Conceptually, the health check can be as elaborate as the deployed
    appliance supports via a custom implementation. At the minimum, and
    by default, the health reflects the status of the cloud instance by
    querying the cloud provider.
    """
    try:
        deployment = models.ApplicationDeployment.objects.get(pk=deployment_id)
        log.debug("Checking health of deployment %s", deployment.name)
        plugin = _get_app_plugin(deployment)
        dpl = _serialize_deployment(deployment)
        provider = domain_model.get_cloud_provider(deployment.target_cloud,
                                                   credentials)
        result = plugin.health_check(provider, dpl)
    except Exception as e:
        msg = "Health check failed: %s" % str(e)
        log.error(msg)
        raise Exception(msg) from e
    finally:
        # We only keep the two most recent health check task results so delete
        # any older ones
        signals.health_check.send(sender=None, deployment=deployment)
    # Schedule a task to migrate results right after task completion
    # Do this as a separate task because until this task completes, we
    # cannot obtain final status or traceback.
    migrate_task_result.apply_async([self.request.id], countdown=1)
    return result


@shared_task(bind=True, time_limit=300, expires=120)
def restart_appliance(self, deployment_id, credentials):
    """
    Restarts this appliances
    """
    try:
        deployment = models.ApplicationDeployment.objects.get(pk=deployment_id)
        log.debug("Performing restart on deployment %s", deployment.name)
        plugin = _get_app_plugin(deployment)
        dpl = _serialize_deployment(deployment)
        provider = domain_model.get_cloud_provider(deployment.target_cloud,
                                                   credentials)
        result = plugin.restart(provider, dpl)
    except Exception as e:
        msg = "Restart task failed: %s" % str(e)
        log.error(msg)
        raise Exception(msg) from e
    # Schedule a task to migrate results right after task completion
    # Do this as a separate task because until this task completes, we
    # cannot obtain final status or traceback.
    migrate_task_result.apply_async([self.request.id], countdown=1)
    return result


@shared_task(bind=True, expires=120)
def delete_appliance(self, deployment_id, credentials):
    """
    Deletes this appliances
    If successful, will also mark the supplied ``deployment`` as
    ``archived`` in the database.
    """
    try:
        deployment = models.ApplicationDeployment.objects.get(pk=deployment_id)
        log.debug("Performing delete on deployment %s", deployment.name)
        plugin = _get_app_plugin(deployment)
        dpl = _serialize_deployment(deployment)
        provider = domain_model.get_cloud_provider(deployment.target_cloud,
                                                   credentials)
        result = plugin.delete(provider, dpl)
        if result is True:
            deployment.archived = True
            deployment.save()
    except Exception as e:
        msg = "Delete task failed: %s" % str(e)
        log.error(msg)
        raise Exception(msg) from e
    # Schedule a task to migrate results right after task completion
    # Do this as a separate task because until this task completes, we
    # cannot obtain final status or traceback.
    migrate_task_result.apply_async([self.request.id], countdown=1)
    return result


class Task(object):
    """
    An abstraction class for handling task actions.

    Plugins can implement the interface defined here and handle task actions
    independent of CloudLaunch and its task broker.
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
