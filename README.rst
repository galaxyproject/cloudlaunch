.. image:: https://travis-ci.org/galaxyproject/cloudlaunch.svg?branch=dev
   :target: https://travis-ci.org/galaxyproject/cloudlaunch
   :alt: Travis Build Status

===========
CloudLaunch
===========

CloudLaunch is a reusable Django app for launching applications on cloud,
container or local infrastructure.

This is an all new version of Cloudlaunch currently being developed as per
`issue #49 <https://github.com/galaxyproject/cloudlaunch/issues/49>`_. Stay
tuned.

Install
-------

Cloudlaunch is based on Python 3.5 and although it may work on older Python
versions, 3.5 is the only supported version.
Use of virtualenv is also highly advised.

1. Checkout cloudlaunch and create environment

.. code-block:: bash

    $ mkdir launcher && cd launcher
    $ virtualenv -p python3 venv --prompt "(cloudlaunch)" && source venv/bin/activate
    $ git clone -b dev git@github.com:galaxyproject/cloudlaunch.git
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

3. Start the development server and visit http://127.0.0.1:8000/admin/
   to define your application and infrastructure properties.

4. Visit http://127.0.0.1:8000/api/v1/ to explore the API.
