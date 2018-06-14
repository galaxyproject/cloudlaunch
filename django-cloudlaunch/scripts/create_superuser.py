"""
Add Django superuser to the database.

Usage:
export ADMIN_USER=username; export ADMIN_PASS=pass; export ADMIN_EMAIL=email; \
cat create_superuser.py | python manage.py shell
"""

from os import environ
from django.contrib.auth.models import User

username = environ.get('DJANGO_ADMIN_USER', 'admin')
password = environ.get('DJANGO_ADMIN_PASSWORD')
email = environ.get('DJANGO_ADMIN_EMAIL', 'admin@galaxyproject.org')

if password and User.objects.filter(username=username).count() == 0:
    User.objects.create_superuser(username, email, password)
    print('Superuser {0} created.'.format(username))
else:
    print('Superuser {0} creation skipped.'.format(username))
