from django.apps import AppConfig

class CloudLaunchConfig(AppConfig):
    name = 'cloudlaunch'

    def ready(self):
        import cloudlaunch.signals  # noqa
