from django.apps import AppConfig


class BaselaunchConfig(AppConfig):
    name = 'baselaunch'

    def ready(self):
        import baselaunch.signals  # noqa
