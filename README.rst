===========
CloudLaunch
===========

CloudLaunch is a reusable Django app for launching applications on cloud,
container or local infrastructure.

This is an all new version of Cloudlaunch currently being developed as per
[issue #49](https://github.com/galaxyproject/cloudlaunch/issues/49). Stay tuned.

Detailed documentation is in the "docs" directory.

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

2. Start the development server and visit http://127.0.0.1:8000/admin/
   to defined your applications.

3. Visit http://127.0.0.1:8000/cloudlaunch/ to launch an application.
