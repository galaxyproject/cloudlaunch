"""App-wide Django signals."""
from celery.utils.log import get_task_logger

from django.dispatch import receiver
from django.dispatch import Signal

from baselaunch import models

LOG = get_task_logger(__name__)

health_check = Signal(providing_args=["deployment"])


@receiver(health_check)
def delete_old_tasks(sender, deployment, **kwargs):
    """
    Delete HEALTH_CHECK task results other than two most recent ones.

    We keep only the two most recent deployment task results while all others
    are deleted when this signal is invoked. This includes only the tasks with
    ``SUCCESS`` status and correspond to the supplied ``deployment``.
    """
    for old_task in models.ApplicationDeploymentTask.objects.filter(
            deployment=deployment,
            _status="SUCCESS",
            action=models.ApplicationDeploymentTask.HEALTH_CHECK).order_by(
                '-updated')[2:]:
        LOG.debug('Deleting old health task %s from deployment %s',
                  old_task.id, deployment.name)
        old_task.delete()
