.. image:: https://coveralls.io/repos/github/galaxyproject/cloudlaunch/badge.svg?branch=dev
   :target: https://coveralls.io/github/galaxyproject/cloudlaunch?branch=dev
   :alt: Test Coverage Report

.. image:: https://travis-ci.org/galaxyproject/cloudlaunch.svg?branch=dev
   :target: https://travis-ci.org/galaxyproject/cloudlaunch
   :alt: Travis Build Status

===========
CloudLaunch
===========

CloudLaunch is a reusable Django app for discovering and launching applications
on cloud, container, or local infrastructure. A live version is available at
https://beta.launch.usegalaxy.org/.

This is an all-new version of Cloudlaunch that replaces the original
BioCloudCentral launcher. Code for that version is available in the
`BioCloudCentral branch <https://github.com/galaxyproject/cloudlaunch/tree/BioCloudCentral>`_.

Install
-------

CloudLaunch is based on Python 3.5 and although it may work on older Python
versions, 3.5 is the only supported version. Use of virtualenv is also highly advised.

1. Checkout cloudlaunch and create environment

.. code-block:: bash

    $ mkdir launcher && cd launcher
    $ virtualenv -p python3.5 venv --prompt "(cloudlaunch)" && source venv/bin/activate
    $ git clone -b dev https://github.com/galaxyproject/cloudlaunch.git
    $ cd cloudlaunch
    $ pip install -r requirements.txt
    $ cd django-cloudlaunch
    $ python manage.py migrate
    $ python manage.py runserver
    $ python manage.py createsuperuser

2. Copy ``cloudlaunch/settings_local.py.sample`` to
   ``cloudlaunch/settings_local.py`` and make any desired configuration
   changes. **Make sure to change** the value for ``FERNET_KEYS`` variable
   because it is used to encrypt sensitive database fields.

3. Start the development server and celery task queue, each process
   in its own tab.

.. code-block:: bash

    $ python manage.py runserver
    $ celery -A cloudlaunch worker -l info

4. Visit http://127.0.0.1:8000/admin/ to define your application and
   infrastructure properties.

5. Visit http://127.0.0.1:8000/api/v1/ to explore the API.

You will probably also want to install the UI for the server. The default UI
is available at https://github.com/galaxyproject/cloudlaunch-ui.
