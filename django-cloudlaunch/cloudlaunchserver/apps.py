import os

import threading

from celery.worker import WorkController

from django.apps import AppConfig
from django.dispatch import Signal, receiver

from .celery import app


class CloudLaunchServerConfig(AppConfig):
    name = 'cloudlaunchserver'

    def ready(self):
        # Only raised during tests when the test server is being shutdown
        django_server_shutdown = Signal()
        if 'test' in os.environ.get('CELERY_CONFIG_MODULE'):
            # Start an in-process threaded celery worker, so that it's not necessary to start
            # a separate celery process during testing.
            # https://stackoverflow.com/questions/22233680/in-memory-broker-for-celery-unit-tests
            # Also refer: https://github.com/celery/celerytest
            app.control.purge()

            def mock_import_module(*args, **kwargs):
                return None

            # ref: https://medium.com/@erayerdin/how-to-test-celery-in-django-927438757daf
            app.loader.import_default_modules = mock_import_module

            worker = WorkController(
                app=app,
                # not allowed to override TestWorkController.on_consumer_ready
                ready_callback=None,
                without_heartbeat=True,
                without_mingle=True,
                without_gossip=True)

            t = threading.Thread(target=worker.start)
            t.daemon = True
            t.start()

            @receiver(django_server_shutdown)
            def on_shutdown(sender, **kwargs):
                # Do nothing. Calling stop results in celery hanging waiting for keyboard input
                # celery_worker.stop()
                pass
