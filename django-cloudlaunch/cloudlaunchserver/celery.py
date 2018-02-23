# File based on:
# http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
from __future__ import absolute_import

import os
import raven

import celery
from django.conf import settings  # noqa
from raven.contrib.celery import register_signal, register_logger_signal

import logging
log = logging.getLogger(__name__)

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudlaunchserver.settings')


class Celery(celery.Celery):

    def on_configure(self):
        client = raven.Client(settings.RAVEN_CONFIG.get('dsn'))

        # register a custom filter to filter out duplicate logs
        register_logger_signal(client)

        # hook into the Celery error handler
        register_signal(client)


app = Celery('proj')
# Changed to use dedicated celery config as detailed in:
# http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html
# app.config_from_object('django.conf:settings')
app.config_from_object('cloudlaunchserver.celeryconfig')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    log.debug('Request: {0!r}'.format(self.request))
