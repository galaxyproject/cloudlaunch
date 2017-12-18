.. cloudlaunch documentation master file, created by
   sphinx-quickstart on Mon Dec 18 16:10:21 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the CloudLaunch documentation!
=========================================

CloudLaunch is a ReSTful, extensible Django app for discovering and launching
applications on cloud, container, or local infrastructure. A live version is
available at https://beta.launch.usegalaxy.org/.

CloudLaunch can be extended with your own plug-ins which can provide custom
launch logic for arbitrary custom applications. Visit the live site to see
currently available applications in the Catalog. CloudLaunch is also tightly
integrated with `CloudBridge <github.com/gvlproject/cloudbridge>`_, which makes
CloudLaunch natively multi-cloud.

CloudLaunch has a web and commandline front-end. The Web UI is maintained in the
`CloudLaunch-UI <https://github.com/galaxyproject/cloudlaunch-ui>`_ repository.
The commandline client is maintained in the
`cloudlaunch-cli <https://github.com/CloudVE/cloudlaunch-cli>`_ repository.

Install
-------

CloudLaunch is based on Python 3.6 and although it may work on older Python
versions, 3.6 is the only supported version. Use of virtualenv is also highly
recommended.

1. Checkout cloudlaunch and create environment

.. code-block:: bash

    $ mkdir launcher && cd launcher
    $ virtualenv venv -p python3.6 --prompt "(cloudlaunch)" && source venv/bin/activate
    $ git clone -b dev https://github.com/galaxyproject/cloudlaunch.git
    $ cd cloudlaunch
    $ pip install -r requirements.txt
    $ cd django-cloudlaunch
    $ python manage.py migrate
    $ python manage.py runserver
    $ python manage.py createsuperuser

2. Copy ``cloudlaunchserver/settings_local.py.sample`` to
   ``cloudlaunchserver/settings_local.py`` and make any desired configuration
   changes. **Make sure to change** the value for ``FERNET_KEYS`` variable
   because it is used to encrypt sensitive database fields.

3. Start the development server and celery task queue (along with a Redis
   server as the message broker), each process in its own tab.

.. code-block:: bash

    $ python manage.py runserver
    $ redis-server & celery -A cloudlaunchserver worker -l info --beat

4. Visit http://127.0.0.1:8000/admin/ to define your application and
   infrastructure properties.

5. Visit http://127.0.0.1:8000/api/v1/ to explore the API.

You will probably also want to install the UI for the server. The default UI
is available at https://github.com/galaxyproject/cloudlaunch-ui.


Documentation
-------------
.. toctree::
   :maxdepth: 2

   topics/overview.rst
   topics/social_auth.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
