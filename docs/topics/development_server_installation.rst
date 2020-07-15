Installation for development
============================

CloudLaunch is made up of three services: the server, the user interface (UI),
and a message queue. All three processes need to run for the application to
function properly. See instructions below on how to install and start each
of the processes.

Install the server
------------------

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
   ``cloudlaunchserver/settings_local.py`` and make any desired configuration
   changes. No change are required for the CloudLaunch to run.

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


Install the UI
--------------

1. Clone the source code repository

.. code-block:: bash

    $ git clone https://github.com/galaxyproject/cloudlaunch-ui.git
    $ cd cloudlaunch-ui

2. Install required libraries

Make sure you have ``node`` (version 6.*) installed. Then install
dependencies with the following commands:

.. code-block:: bash

    # Install typescript development support
    npm install -g tsd
    # Install angular-cli
    npm install -g @angular/cli
    # Install dependencies
    npm install

3. Run the development server

Start the development server with

.. code-block:: bash

    npm start

Or if you use yarn as your preferred package manager, ``yarn start``.

Access the server at ``http://localhost:4200/``. The app will
automatically reload if you change any of the source files.
