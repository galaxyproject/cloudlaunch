import os

# You probably do not want to edit these settings
PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))
SESSION_ENGINE = "django.contrib.sessions.backends.db"
REDIRECT_BASE = None

#
# Edit the following Django settings
#

# Set the desired database, sqlite for local/dev installations works good;
# Postgres is better and should definitely be enabled for production installs.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2' or 'sqlite3'.
        'NAME': os.path.join(PROJECT_ROOT, 'db', 'db.sqlite'),  # Or path to database file if using sqlite3.
        'USER': '',      # Not used with sqlite3.
        'PASSWORD': '',  # Not used with sqlite3.
        'HOST': '',      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',      # Set to empty string for default. Not used with sqlite3.
    }
}

# Set this absolute path then run: python biocloudcentral/manage.py collectstatic
STATIC_ROOT = '/Users/niteshturaga/Documents/cloud.bioconductor/cloudlaunch/static_content'


#
# App-specific settings (i.e., not Django-related)
#

# Page title and brand text
BRAND = "Bioconductor Cloud Launch"
# Supply a string that will be prominently displayed on the launch page.
# You can use HTML tags as part of the string.
NOTICE = None

# Whether to add an email field to the form and make it required or optional.
ASK_FOR_EMAIL = False
REQUIRE_EMAIL = False
