from __future__ import absolute_import

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app  # noqa

__all__ = ['celery_app']

default_app_config = 'cloudlaunchserver.apps.CloudLaunchServerConfig'

# Current version of the library
__version__ = '2.0.2'


def get_version():
    """
    Return a string with the current version of the library.

    :rtype: ``string``
    :return:  Library version (e.g., "2.0.2").
    """
    return __version__