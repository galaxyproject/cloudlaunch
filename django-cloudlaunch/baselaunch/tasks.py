"""Tasks to be executed asynchronously (via Celery)."""
import copy
import json

from celery.app import shared_task
from celery.result import AsyncResult

from baselaunch import models
from baselaunch import util


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
    handler = util.import_class(
        cloud_version_config.application_version.backend_component_name)()
    launch_result = handler.launch_app(launch_appliance, name,
                                       cloud_version_config, credentials,
                                       app_config, user_data)
    migrate_task_result.apply_async([launch_appliance.request.id],
                                    countdown=3600)
    return launch_result
    # print("Running launch app task")
    # sleep(30)
    # # Schedule a task to migrate result one hour from now
    # migrate_task_result.apply_async([launch_appliance.request.id],
    #                                 countdown=60)
    # return {'cl': 'dummy'}
