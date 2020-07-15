.. image:: https://readthedocs.org/projects/cloudlaunch/badge/?version=latest
   :target: http://cloudlaunch.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

===========
CloudLaunch
===========

CloudLaunch is a ReSTful, extensible Django app for discovering and launching
applications on cloud, container, or local infrastructure. A live version is
available at https://launch.usegalaxy.org/.

CloudLaunch can be extended with your own plug-ins, which can provide custom
launch logic for arbitrary applications. Visit the live site to see
currently available applications in the Catalog. CloudLaunch is also tightly
integrated with `CloudBridge <https://github.com/gvlproject/cloudbridge>`_,
which makes CloudLaunch natively multi-cloud. If you would like to have an
additional cloud provider added as an available option for a given appliance,
please create an issue in this repo.

CloudLaunch has a web and commandline front-end. The Web UI is maintained in the
`CloudLaunch-UI <https://github.com/galaxyproject/cloudlaunch-ui>`_ repository.
The commandline client is maintained in the
`cloudlaunch-cli <https://github.com/CloudVE/cloudlaunch-cli>`_ repository.

Installation
------------

On Kuberneets, via Helm
***********************
The recommended way to install CloudLaunch is via the CloudLaunch Helm Chart:
https://github.com/cloudve/cloudlaunch-helm


Locally, via commandline
************************

1. Install the CloudLaunch Django server

.. code-block:: bash

    $ pip install cloudlaunch-server

Once installed, you can run Django admin commands as follows:

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

4. Start the development server and celery task queue (along with a Redis
   server as the message broker), each process in its own tab.

.. code-block:: bash

    $ python manage.py runserver
    $ redis-server & celery -A cloudlaunchserver worker -l info --beat

5. Visit http://127.0.0.1:8000/cloudlaunch/admin/ to define your application and
   infrastructure properties.

6 . Install the UI for the server by following instructions from
    https://github.com/galaxyproject/cloudlaunch-ui.


Install Development Version
---------------------------

CloudLaunch is based on Python 3.6 and although it may work on older Python
versions, 3.6 is the only supported version. Use of Conda or virtualenv is also
highly advised.

1. Checkout CloudLaunch and create an isolated environment

.. code-block:: bash

    $ conda create --name cl --yes python=3.6
    $ conda activate cl
    $ git clone https://github.com/galaxyproject/cloudlaunch.git
    $ cd cloudlaunch
    $ pip install -r requirements_dev.txt
    $ cd django-cloudlaunch

2. Copy ``cloudlaunchserver/settings_local.py.sample`` to
   ``cloudlaunchserver/settings_local.py`` and make any desired configuration changes.

3. Run the migrations and create a superuser:

.. code-block:: bash

    $ python manage.py migrate
    $ python manage.py createsuperuser

4. Start the web server and Celery in separate tabs

.. code-block:: bash

    $ python manage.py runserver
    $ redis-server & celery -A cloudlaunchserver worker -l info --beat

5. Visit http://127.0.0.1:8000/cloudlaunch/admin/ to define appliances and
   add cloud providers.

6. Visit http://127.0.0.1:8000/cloudlaunch/api/v1/ to explore the API.

7 . Install the UI for the server by following instructions from
    https://github.com/galaxyproject/cloudlaunch-ui.


Contributing
------------

Every PR should also bump the version or build number. Do this by running one
of the following commands as part of the PR, which will create a commit:

- For updating a dev version: ``bumpversion [major | minor | patch]``
  eg, with current version 4.0.0, running ``bumpversion patch`` will result in
  *4.0.1-dev0*

- For updating a build version: ``bumpversion build`` will result in
  *4.0.1-dev1*

- For production version: ``bumpversion --tag release`` will result
  in *4.0.1*, with a git tag
