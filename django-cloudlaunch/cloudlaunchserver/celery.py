# File based on:
# http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
from __future__ import absolute_import

import logging
import os

import celery

from django.conf import settings  # noqa

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

log = logging.getLogger(__name__)

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudlaunchserver.settings')

# Set default configuration module name
os.environ.setdefault('CELERY_CONFIG_MODULE', 'cloudlaunchserver.celeryconfig')


class Celery(celery.Celery):

    def on_configure(self):
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN, integrations=[CeleryIntegration()])


app = Celery('proj')
# Changed to use dedicated celery config as detailed in:
# http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html
# app.config_from_object('django.conf:settings')
app.config_from_envvar('CELERY_CONFIG_MODULE')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    log.debug('Request: {0!r}'.format(self.request))
