## Cloud Launch

Easily launch [Galaxy][8], [CloudMan][2], and [CloudBioLinux][3] platforms without
any configuration. You can use this app directly on [biocloudcentral.org][7] or
run it locally - either way, it takes about 2 minutes to go from nothing to
a configured cluster-in-the-cloud and a scalable analysis platform on top of
cloud resources.

### Installing a dev instance

This [Django][1] application can be run locally for development, start by installing Python and [virtualenv][5]. Then, build a virtualenv and install the dependencies:

    $ mkdir cl; cd cl
    $ virtualenv .
    $ source bin/activate
    $ git clone https://github.com/galaxyproject/cloudlaunch.git
    $ cd cloudlaunch
    $ pip install -r requirements.txt

Next, you need to make a database available. For development,
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

#### Run the app

Start the app with the following command, which will start a development web
server and a task queue process:

    $ honcho -f ProcfileDev start

The application will be available on port 8000 (``127.0.0.1:8000``).
The Admin part of the app is available under ``127.0.0.1:8000/admin/``, where you
will need to add your cloud connection and image information before you can launch
instances.

Alternatively, you start the web server and the Celery task queue
in two separate tabs (or [screen][10] sessions):

    $ python biocloudcentral/manage.py runserver
    $ python biocloudcentral/manage.py celeryd --concurrency 2 --loglevel=debug

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

        $ sudo apt-get update
        $ sudo apt-get -y install python-virtualenv git postgresql libpq-dev postgresql-server-dev-all python-dev nginx supervisor

- Clone Cloud Launch into a local directory ``/srv/cloudlaunch`` as
system user ``launch`` and install the required libraries (if you choose to install the app in a different directory, you will also need to change a number of configuration files where the specified path is assumed):

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
    - Ensure ``STATIC_ROOT`` is set to ``/srv/cloudlaunch/media``
        - Make sure the set directory exists and is owned by the `launch` user
    - Change ``SECRET_KEY``

- Apply database migrations as per above section

- Collect all static files into a single directory by running:

        $ cd /srv/cloudlaunch/cloudlaunch
        $ python biocloudcentral/manage.py collectstatic --noinput

- Configure nginx:

    - If it exists, delete ``default`` site from ``/etc/nginx/sites-enabled``
      (or update it as necessary)

            $ sudo rm /etc/nginx/sites-enabled/default

    - Copy the nginx config file from the Cloud Launch repo

            $ sudo cp /srv/cloudlaunch/cloudlaunch/cl_nginx.conf /etc/nginx/sites-available/

    - Create the following symlink

            $ sudo ln -s /etc/nginx/sites-available/cl_nginx.conf /etc/nginx/sites-enabled/cl

    - Optionally update the number of worker threads in ``/etc/nginx/nginx.conf``
    - Test the nginx configuration with ``sudo nginx -t``
    - Start & reload nginx with ``sudo service nginx start`` and ``sudo nginx -s reload``

- Run the app via [supervisor][17]:

        $ sudo cp cl_supervisor.conf /etc/supervisor/conf.d/
        $ sudo supervisorctl reread
        $ sudo supervisorctl update
        # Check the status with
        $ sudo supervisorctl status

- The app is now available at ``http://server.ip.address/``. The Admin part of
the app is available at ``http://server.ip.address/admin/``.

- Logs are available in the installation directory, `/srv/cloudlaunch/cloudlaunch/`

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
[17]: http://supervisord.org/index.html

## LICENSE

The code is freely available under the [MIT license][l1].

[l1]: http://www.opensource.org/licenses/mit-license.html
