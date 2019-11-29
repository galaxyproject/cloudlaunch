#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys

from setuptools import setup
from setuptools import find_packages


def get_version(*file_paths):
    """Retrieves the version from django-cloudlaunch/__init__.py"""
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    version_file = open(filename).read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


version = get_version("django-cloudlaunch", "cloudlaunchserver", "__init__.py")


if sys.argv[-1] == 'publish':
    try:
        import wheel
        print("Wheel version: ", wheel.__version__)
    except ImportError:
        print('Wheel library missing. Please run "pip install wheel"')
        sys.exit()
    os.system('python setup.py sdist upload')
    os.system('python setup.py bdist_wheel upload')
    sys.exit()

if sys.argv[-1] == 'tag':
    print("Tagging the version on git:")
    os.system("git tag -a %s -m 'version %s'" % (version, version))
    os.system("git push --tags")
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

REQS_BASE = [
    'Django>=2.0',
    # ======== Celery =========
    'celery>=4.1',
    # celery results backend which uses the django DB
    'django-celery-results>=1.0.1',
    # celery background task monitor which uses the django DB
    'django-celery-beat>=1.3.0',
    # ======== DRF =========
    'djangorestframework>=3.7.3',
    # login support for DRF through restful endpoints
    'django-rest-auth>=0.9.1',
    # pluggable social auth for django login
    'django-allauth>=0.34.0',
    # Provides nested routing for DRF
    'drf-nested-routers>=0.90.0',
    # For DRF filtering by querystring
    'django-filter>=1.1.0',
    # Provides REST API schema
    'coreapi>=2.2.3',
    # ======== CloudBridge =========
    'cloudbridge',
    'djcloudbridge',
    # ======== Django =========
    # Provides better inheritance support for django models
    'django-model-utils',
    # for encryption of user credentials
    'django-fernet-fields>=0.5',
    # Middleware for automatically adding CORS headers to responses
    'django-cors-headers>=2.1.0',
    # for nested object editing in django admin
    'django-nested-admin>=3.0.21',
    # For dependencies between key fields in django admin
    'django-autocomplete-light>=3.3.2',
    # ======== Public Appliances =========
    # Used by public_appliances for retrieving country data
    'django-countries>=5.0',
    # ======== Misc =========
    # For the CloudMan launcher
    'bioblend',
    # For merging userdata/config dictionaries
    'jsonmerge>=1.4.0',
    # For commandline option handling
    'click',
    # Integration with Sentry
    'sentry-sdk==0.6.9',
    # For CloudMan2 plugin
    'gitpython',
    'ansible',
    # Utility package for retrying operations
    'retrying',
    # For serving static files in production mode
    'whitenoise[brotli]'
]

REQS_PROD = ([
    # postgres database driver
    'psycopg2-binary',
    'gunicorn[gevent]'] + REQS_BASE
)

REQS_TEST = ([
    'pydevd',
    'sqlalchemy',  # for celery results backend
    'tox>=2.9.1',
    'coverage>=4.4.1',
    'flake8>=3.4.1',
    'flake8-import-order>=0.13'] + REQS_BASE
)

REQS_DEV = ([
    # As celery message broker during development
    'redis',
    'sphinx>=1.3.1',
    'bumpversion>=0.5.3',
    'pylint-django'] + REQS_TEST
)

setup(
    name='cloudlaunch-server',
    version=version,
    description=("CloudLaunch is a ReSTful, extensible Django app for"
                 " discovering and launching applications on cloud, container,"
                 " or local infrastructure"),
    long_description=readme + '\n\n' + history,
    author='Galaxy Project',
    author_email='help@cloudve.org',
    url='https://github.com/galaxyproject/cloudlaunch',
    package_dir={'': 'django-cloudlaunch'},
    packages=find_packages('django-cloudlaunch'),
    package_data={
        'cloudlaunch': [
            'backend_plugins/cloudman2/rancher2_aws_iam_policy.json',
            'backend_plugins/cloudman2/rancher2_aws_iam_trust_policy.json'],
    },
    include_package_data=True,
    install_requires=REQS_BASE,
    extras_require={
        'dev': REQS_DEV,
        'test': REQS_TEST,
        'prod': REQS_PROD
    },
    entry_points={
        'console_scripts': [
            'cloudlaunch-server = cloudlaunchserver.runner:main']
    },
    license="MIT",
    keywords='cloudlaunch',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django',
        'Framework :: Django :: 2.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application'
    ],
)
