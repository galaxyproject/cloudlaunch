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

SECRET_KEY = os.environ.get('CLOUDLAUNCH_SECRET_KEY') or SECRET_KEY

# Read fernet keys from env or default to existing settings keys
ENV_FERNET_KEYS = os.environ.get('CLOUDLAUNCH_FERNET_KEYS')
if ENV_FERNET_KEYS:
    ENV_FERNET_KEYS = ENV_FERNET_KEYS.split(",")
try:
    # Use FERNET_KEYS defined in cloudlaunchserver.settings if defined
    FERNET_KEYS = ENV_FERNET_KEYS or FERNET_KEYS
except NameError:
    FERNET_KEYS = ENV_FERNET_KEYS
