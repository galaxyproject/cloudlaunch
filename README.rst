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

Social auth setup
-----------------

After you have setup the server, you will probably want to setup social
auth to be able to log in using an external service. This setup is required
for end-users so they can self register. If you are setting this up on
localhost, use GitHub or Twitter.

Integration with GitHub
~~~~~~~~~~~~~~~~~~~~~~~

1. Register your server with GitHub: Visit your Github account Settings →
   `Developer settings <https://github.com/settings/developers>`_ and add a new
   OAuth application. Settings should look as in the following screenshot. Note
   port 4200 on the *Authorization callback URL*; this needs to match the port on
   which the CloudLaunch UI is served (4200 is the default). Also take note of the
   *Client ID* and *Client Secret* at the top of that page as we'll need that back
   in CloudLaunch.

.. image:: https://s3.amazonaws.com/cloudlaunchapp/github-oauth-app.png

2. Back on the local server, login to Django admin and change the domain of
   example.com in Sites to ``http://127.0.0.1:8080``. To login to Admin, you'll
   need the superuser account info that was created when setting up the server.

3. Still in Django Admin, now navigate to  *Social Accounts → Social
   applications* and add a new application. Select GitHub as the provider, supply a
   desired application name, and enter the *Client ID* and *Client Secret* we got
   from GitHub. Also choose the site we updated in Step 2.

.. image:: https://s3.amazonaws.com/cloudlaunchapp/add-social-app.png

Save the model and integration with GitHub is complete! You can now log in to
the CloudLaunch UI using Github.


Intergation with Twitter
~~~~~~~~~~~~~~~~~~~~~~~~

1. Register your dev server under your Twitter account. Visit
   https://apps.twitter.com/, click *Create New App*, and fill out the form as in
   the following screenthot. Once the app has been added, click on the *Keys and
   Access Tokens* tab and take a note of *Consumer Key (API Key)* and *Consumer
   Secret (API Secret)*.

.. image:: https://s3.amazonaws.com/cloudlaunchapp/twitter-oauth-app.png

2. Proceed with the same steps as in the docs about about GitHub integration,
   supplying the *Consumer Key (API Key)* and *Consumer Secret (API Secret)* as the
   values of *Client ID* and *Client Secret* for the new defintion of the Social
   application.
