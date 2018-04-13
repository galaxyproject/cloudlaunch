# File based on:
# http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html
from __future__ import absolute_import

import os
import raven

import celery
from django.conf import settings  # noqa
from django.dispatch import Signal, receiver
from raven.contrib.celery import register_signal, register_logger_signal

import logging
log = logging.getLogger(__name__)

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cloudlaunchserver.settings')

# Set default configuration module name
os.environ.setdefault('CELERY_CONFIG_MODULE', 'cloudlaunchserver.celeryconfig')


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
app.config_from_envvar('CELERY_CONFIG_MODULE')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Only raised during tests when the test server is being shutdown
django_server_shutdown = Signal()
if 'test' in os.environ.get('CELERY_CONFIG_MODULE'):
    # Start an in-process threaded celery worker, so that it's not necessary to start
    # a separate celery process during testing.
    # https://stackoverflow.com/questions/22233680/in-memory-broker-for-celery-unit-tests
    # Also refer: https://github.com/celery/celerytest
    app.control.purge()
    celery_worker = app.Worker(app=app, pool='solo', concurrency=1)
    #connections.close_all()
    worker_thread = threading.Thread(target=celery_worker.start)
    worker_thread.daemon = True
    worker_thread.start()

    @receiver(django_server_shutdown)
    def on_shutdown(sender, **kwargs):
        # Do nothing. Calling stop results in celery hanging waiting for keyboard input
        # celery_worker.stop()
        pass


@app.task(bind=True)
def debug_task(self):
    log.debug('Request: {0!r}'.format(self.request))
