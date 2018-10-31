from django.apps import AppConfig

class CloudLaunchConfig(AppConfig):
    name = 'cloudlaunch'

    def ready(self):
        import cloudlaunch.signals  # noqa
        from django.contrib.auth.models import User  # noqa
        from django.contrib.auth.signals import user_logged_in  # noqa
        from django.db.models.signals import post_save  # noqa

        from djcloudbridge.signals import create_profile_at_login  # noqa
        from djcloudbridge.signals import create_profile_with_user  # noqa
        user_logged_in.connect(create_profile_at_login)
        post_save.connect(create_profile_with_user, sender=User)
