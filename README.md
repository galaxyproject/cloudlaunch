## Cloud Launch

Easily launch [Galaxy][8], [CloudMan][2], and [CloudBioLinux][3] platforms without
any configuration. You can use this app directly on [biocloudcentral.org][7] or
run it locally - either way, it takes about 2 minutes to go from nothing to
a configured cluster-in-the-cloud and a scalable analysis platform on top of
cloud resources.

### Installing locally

This [Django][1] application can be run locally, on a dedicated server or deployed
on [Heroku][4]. To run locally or on a dedicated server, start by installing Python
and [virtualenv][5]. Then, build a virtualenv and install the dependencies:

    $ mkdir cl; cd cl
    $ virtualenv .
    $ source bin/activate
    $ git clone https://github.com/galaxyproject/cloudlaunch.git
    $ cd cloudlaunch
    $ pip install -r requirements.txt

Next, you need to make a database available. For local development and deployment,
[SQLite][16] will suffice. To use it, simply copy file
``biocloudcentral/settings_local.py.sample`` to ``biocloudcentral/settings_local.py``
and proceed with the database migrations step below:

    $ cp biocloudcentral/settings_local.py.sample biocloudcentral/settings_local.py
    $ mkdir biocloudcentral/db

#### Applying database migrations

Finally, apply the database migrations, and, optionally, preload your database
with the details about [AWS instances][9]. When prompted during the initial
databse sync, create a super-user account; it will be used to log into the
Admin side of the app and allow you to manage it:

    $ python biocloudcentral/manage.py syncdb
    $ python biocloudcentral/manage.py migrate biocloudcentral
    $ python biocloudcentral/manage.py migrate djcelery
    $ python biocloudcentral/manage.py migrate kombu.transport.django
    # Optional; if you want to preload AWS cloud info and instance types
    $ python biocloudcentral/manage.py loaddata biocloudcentral/aws_db_data.json

#### Collect static data

Do the following to get all the static content into a single location:

    $ mkdir /some/absolute/path
    # Edit biocloudcentral/settings_local.py and set STATIC_ROOT to above path
    $ python biocloudcentral/manage.py collectstatic --noinput

#### Running locally

Simply run:

    $ honcho -f ProcfileHoncho start

The application will be available on port 5000 (``127.0.0.1:5000``).
The Admin part of the app is available under ``127.0.0.1:5000/admin/``.

Alternatively, you start the web server and the Celery workers
in two separate tabs (or [screen][10] sessions):

    $ python biocloudcentral/manage.py runserver
    $ python biocloudcentral/manage.py celeryd --concurrency 2 --loglevel=info

In this case, the application will be available on localhost on port
8000 (``http://127.0.0.1:8000``).

### Deploying to Heroku

An instance of this app available at [biocloudcentral.org][7] is hosted on
[Heroku][11]. You can do the same by [registering][12] and [deploying][13] the app
under your own account. To get started, add heroku as a remote repository:

    $ git remote add heroku git@heroku.com:biocloudcentral.git

Then, automatically [push to Heroku for live deployment][14]:

    $ git push heroku master

If the database needs migration, run:

    $ heroku run python biocloudcentral/manage.py migrate

### Configuring on a dedicated production server

- Launch a Ubuntu 14.04 instance or a VM
- Install necessary system packages:

        $ sudo apt-get -y install python-virtualenv git postgresql libpq-dev postgresql-server-dev-all python-dev nginx

- Clone Cloud Launch into a local directory (e.g., ``/srv/cloudlaunch``) as
system user ``launch`` and install the required libraries:

        $ sudo mkdir -p /srv/cloudlaunch
        $ sudo chown launch:launch /srv/cloudlaunch
        $ cd /srv/cloudlaunch
        $ virtualenv .cl
        $ source .cl/bin/activate
        $ git clone https://github.com/galaxyproject/cloudlaunch.git
        $ cd cloudlaunch
        $ pip install -r requirements.txt

- Configure a [PostgreSQL][15] server with a database. Note that
the following commands use *launch* as the database owner. If you prefer to use
a different user, change it in both commands:

        $ sudo su postgres -c "psql --port 5432 -c \"CREATE ROLE launch LOGIN CREATEDB PASSWORD 'password_to_change'\""
        $ sudo su launch -c "createdb --username launch --port 5432 cloudlaunch"

- Make a copy of ``biocloudcentral/settings_local.py.sample`` as
``biocloudcentral/settings_local.py`` and set (at least) the following values:

    - Edit the database settings to point to the installed Postgres DB. These must
    match the username, port, and password from the previous two commands. Delete
    or comment out any other ``DATABASE`` fields in the file.

            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql_psycopg2',
                    'NAME': 'cloudlaunch',
                    'USER': 'launch',
                    'PASSWORD': 'password_to_change',
                    'HOST': 'localhost',
                    'PORT': '5432',
                }
            }

    - Set admin users
    - Update ``STATIC_ROOT`` if ``/srv/cloudlaunch/media`` is not acceptable
        - Make sure the set directory exists and is owned by the `launch` user
    - Change ``SECRET_KEY``

- Apply database migrations as per above section

- Collect all static files into a single directory by running:

        $ cd /srv/cloudlaunch/cloudlaunch
        $ python biocloudcentral/manage.py collectstatic --noinput

- Create an empty log file that can be edited by the ``launch`` user

        $ sudo touch /var/log/cl_server.log
        $ sudo chown launch:launch /var/log/cl_server.log

- Copy Upstart files (``cl.conf`` and ``cl_celery.conf``) to ``/etc/init``

        $ sudo cp cl.conf cl_celery.conf /etc/init/.

- Configure nginx:

    - If it exists, delete ``default`` site from ``/etc/nginx/sites-enabled``
      (or update it as necessary)

            $ sudo rm /etc/nginx/sites-enabled/default

    - Copy the nginx config file from the Cloud Launch repo

            $ sudo cp cl_nginx.conf /etc/nginx/sites-available/

    - Create the following symlink

            $ sudo ln -s /etc/nginx/sites-available/cl_nginx.conf /etc/nginx/sites-enabled/cl

    - Optionally update the number of worker threads in ``/etc/nginx/nginx.conf``
    - Test the nginx configuration with ``sudo nginx -t``
    - Start ``sudo service nginx start`` or reload nginx: ``sudo nginx -s reload``

- Start the app services via Upstart:

        $ sudo service cl start
        $ sudo service cl_celery start

- The app is now available at ``https://server.ip.address/``. The Admin part of
the app is available at ``https://server.ip.address/admin/``.

[1]: https://www.djangoproject.com/
[2]: http://usecloudman.org/
[3]: http://cloudbiolinux.org/
[4]: http://devcenter.heroku.com/articles/django
[5]: https://github.com/pypa/virtualenv
[6]: https://github.com/chapmanb/biocloudcentral/blob/master/biocloudcentral/settings.py
[7]: http://biocloudcentral.org/
[8]: http://usegalaxy.org/
[9]: http://aws.amazon.com/ec2/#instance
[10]: http://www.gnu.org/software/screen/
[11]: https://www.heroku.com/
[12]: https://devcenter.heroku.com/articles/quickstart
[13]: https://devcenter.heroku.com/articles/django
[14]: https://devcenter.heroku.com/articles/git
[15]: http://www.postgresql.org/
[16]: http://www.sqlite.org/

## LICENSE

The code is freely available under the [MIT license][l1].

[l1]: http://www.opensource.org/licenses/mit-license.html
