from __future__ import absolute_import

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app  # noqa

__all__ = ['celery_app']

default_app_config = 'cloudlaunchserver.apps.CloudLaunchServerConfig'

# Current version of the library
# Do not edit this number by hand. See Contributing section in the README.
__version__ = '4.0.0'



def get_version():
    """
    Return a string with the current version of the library.

    :rtype: ``string``
    :return:  Library version (e.g., "4.0.0").
    """
    return __version__
