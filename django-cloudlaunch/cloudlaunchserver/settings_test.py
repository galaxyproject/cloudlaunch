"""
Django settings used during cloudlaunch testing
"""
from cloudlaunchserver.settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/cloudlaunch_testdb.sqlite3',
    }
}
