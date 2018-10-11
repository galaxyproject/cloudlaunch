.. image:: https://readthedocs.org/projects/cloudlaunch/badge/?version=latest
   :target: http://cloudlaunch.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

===========
CloudLaunch
===========

CloudLaunch is a ReSTful, extensible Django app for discovering and launching
applications on cloud, container, or local infrastructure. A live version is
available at https://launch.usegalaxy.org/.

CloudLaunch can be extended with your own plug-ins which can provide custom
launch logic for arbitrary custom applications. Visit the live site to see
currently available applications in the Catalog. CloudLaunch is also tightly
integrated with `CloudBridge <https://github.com/gvlproject/cloudbridge>`_,
which makes CloudLaunch natively multi-cloud.

CloudLaunch has a web and commandline front-end. The Web UI is maintained in the
`CloudLaunch-UI <https://github.com/galaxyproject/cloudlaunch-ui>`_ repository.
The commandline client is maintained in the
`cloudlaunch-cli <https://github.com/CloudVE/cloudlaunch-cli>`_ repository.

This is an all-new version of CloudLaunch that replaces the original
BioCloudCentral launcher. Code for that version is available in the
`BioCloudCentral branch <https://github.com/galaxyproject/cloudlaunch/tree/BioCloudCentral>`_.

Install Production Version
--------------------------

1. Install the cloudlaunch django server

.. code-block:: bash

    $ pip install cloudlaunch-server

Once installed, You can run django admin commands as follows:

.. code-block:: bash

    $ cloudlaunch-server django

2. Copy ``cloudlaunchserver/settings_local.py.sample`` to
   ``cloudlaunchserver/settings_local.py`` and make any desired configuration
   changes. **Make sure to change** the value for ``FERNET_KEYS`` variable
   because it is used to encrypt sensitive database fields.

3. Prepare the database with:

.. code-block:: bash

    $ cloudlaunch-server django migrate
    $ cloudlaunch-server django createsuperuser
    $ cloudlaunch-server django runserver

4. Start the development server and celery task queue (along with a Redis
   server as the message broker), each process in its own tab.

.. code-block:: bash

    $ python manage.py runserver
    $ redis-server & celery -A cloudlaunchserver worker -l info --beat

5. Visit http://127.0.0.1:8000/admin/ to define your application and
   infrastructure properties.

6. Visit http://127.0.0.1:8000/api/v1/ to explore the API.

You will probably also want to install the UI for the server. The default UI
is available at https://github.com/galaxyproject/cloudlaunch-ui.


Install Development Version
----------------------------

CloudLaunch is based on Python 3.6 and although it may work on older Python
versions, 3.6 is the only supported version. Use of virtualenv is also highly advised.

1. Checkout cloudlaunch and create environment

.. code-block:: bash

    $ mkdir launcher && cd launcher
    $ virtualenv venv -p python3.6 --prompt "(cloudlaunch)" && source venv/bin/activate
    $ git clone -b dev https://github.com/galaxyproject/cloudlaunch.git
    $ cd cloudlaunch
    $ python setup.py develop
    $ cd django-cloudlaunch
    $ python manage.py migrate
    $ python manage.py runserver
    $ python manage.py createsuperuser

2. Follow step 2 onwards from the production instructions above
