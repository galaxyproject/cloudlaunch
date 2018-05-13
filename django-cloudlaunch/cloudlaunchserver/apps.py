import os
import threading

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
