"""
Django settings used during cloudlaunch production
"""

from cloudlaunchserver.settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.' + os.environ.get('CLOUDLAUNCH_DB_ENGINE', 'sqlite3'),
        'NAME': os.environ.get('CLOUDLAUNCH_DB_NAME', os.path.join(BASE_DIR, 'db.sqlite3')),
        'USER': os.environ.get('CLOUDLAUNCH_DB_USER'),
        'HOST': os.environ.get('CLOUDLAUNCH_DB_HOST'),
        'PORT': os.environ.get('CLOUDLAUNCH_DB_PORT'),
        'PASSWORD': os.environ.get('CLOUDLAUNCH_DB_PASSWORD'),
    }
}
