# File based on:
# http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
from __future__ import absolute_import

import os

from celery import Celery
from django.conf import settings  # noqa

import logging
log = logging.getLogger(__name__)

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudlaunch.settings')

app = Celery('proj')

# Using a string here means the worker will not have to
# pickle the object when using Windows.

# Changed to use dedicated celery config as detailed in:
# http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html
# app.config_from_object('django.conf:settings')
app.config_from_object('cloudlaunch.celeryconfig')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    log.debug('Request: {0!r}'.format(self.request))
