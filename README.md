## BioCloudCentral

Easily launch [CloudBioLinux][3], [CloudMan][2] and [Galaxy][8] platforms without
any configuration. You can use this app directly on [biocloudcentral.org][7] or
run it locally - either way, it takes about 2 minutes to go from nothing to
a configured cluster-in-the-cloud and a scalable analysis platform on top of
cloud resources.

### Installing locally

This [Django][1] application can be run locally, on a dedicated server or deployed
on [Heroku][4]. To run locally or on a dedicated server, start by installing Python
and [virtualenv][5]. Then, build a virtualenv and install the dependencies:

    $ mkdir bcc; cd bcc
    $ virtualenv .
    $ source bin/activate
    $ git clone git@github.com:chapmanb/biocloudcentral.git
    $ cd biocloudcentral
    $ pip install -r requirements.txt

Next, you need to make a database available. For local development and deployment,
[SQLite][16] will suffice. To use it, simply copy file
``biocloudcentral/settings_local.py.sample`` to ``biocloudcentral/settings_local.py``
and proceed with the database migrations step below:

    $ cp biocloudcentral/settings_local.py.sample biocloudcentral/settings_local.py
    $ mkdir biocloudcentral/db

#### Applying database migrations

Finally, apply the database migrations, and, optionally, preload your database
with the details about [AWS instances][9]. When prompted, there is no requirement to
create a super-user account when asked. However, it may be desirable to be able
to log into the Admin side of the app:

    $ python biocloudcentral/manage.py syncdb
    $ python biocloudcentral/manage.py migrate biocloudcentral
    $ python biocloudcentral/manage.py migrate djcelery
    $ python biocloudcentral/manage.py migrate kombu.transport.django
    $ python biocloudcentral/manage.py loaddata biocloudcentral/aws_db_data.json

#### Running locally

Simply start the web server and the Celery workers (in two separate tabs or
[screen][10] sessions):

    $ python biocloudcentral/manage.py runserver
    $ python biocloudcentral/manage.py celeryd --concurrency 3 --loglevel=info

By default, the application will be available on localhost on port 8000
(``127.0.0.1:8000``).

### Deploying to Heroku

The main instance of this app available at [biocloudcentral.org][7] is hosted on
[Heroku][11]. You can do the same by [registering][12] and [deploying][13] the app
under your own account. Once setup, automatically [push to Heroku for live deployment][14]:

    $ git remote add heroku git@heroku.com:biocloudcentral.git
    $ git push heroku master

### Configuring on a dedicated production server

- Launch a Ubuntu 12.04 instance or a VM
- Install necessary system packages:

        $ sudo apt-get install python-virtualenv git postgresql libpq-dev postgresql-server-dev-all python-dev nginx

- Clone BioCloudCentral into a local directory (e.g., ``/gvl/bcc``) and install
the required libraries:

        $ sudo mkdir -p /gvl/bcc
        $ sudo chown ubuntu:ubuntu -R /gvl/bcc
        $ cd /gvl/bcc
        $ virtualenv .
        $ source bin/activate
        $ git clone https://github.com/chapmanb/biocloudcentral.git
        $ cd biocloudcentral
        $ pip install -r requirements.txt

- Configure a production database, [PostgreSQL][15], with a database. Note that
the following commands use *ubuntu* as the database owner. If you prefer to use
a different user, change it in both commands:

        $ sudo su postgres -c "psql --port 5432 -c \"CREATE ROLE ubuntu LOGIN CREATEDB PASSWORD 'password_to_change'\""
        $ createdb --username ubuntu --port 5432 biocloudcentral

- Update settings in ``biocloudcentral/settings.py`` to match your server settings:

    - Edit the database settings to point to the installed Postgres DB. These must
    match the username, port, and password from the previous two commands. Delete
    or comment out any other ``DATABASE`` fields in the file.

            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql_psycopg2',
                    'NAME': 'biocloudcentral',
                    'USER': 'ubuntu',
                    'PASSWORD': 'password_to_change',
                    'HOST': 'localhost',
                    'PORT': '5432',
                }
            }

    - Set ``DEBUG`` to ``False``
    - Set admin users
    - Set ``REDIRECT_BASE`` to ``None``
    - Set ``STATIC_ROOT`` to ``/gvl/bcc/media`` (and create that dir)
    - Set ``SESSION_ENGINE`` to ``django.contrib.sessions.backends.db``
    - Change ``SECRET_KEY``

- Apply database migrations as per above section

- Collect all static files into a single directory by running:

        $ cd /gvl/bcc/biocloudcentral
        $ python biocloudcentral/manage.py collectstatic  # (type ``yes`` when prompted
        about rewriting existing files)

- Create an empty log file that can be edited by the ``ubuntu`` user

        $ sudo touch /var/log/bcc_server.log
        $ sudo chown ubuntu:ubuntu /var/log/bcc_server.log

- Make sure settings in ``bcc_run_server.sh`` are correct for what you chose above
and then make the file executable

        $ chmod +x bcc_run_server.sh

- Copy Upstart files (``bcc.conf`` and ``bcc_celery.conf``) to ``/etc/init``

        $ sudo cp bcc.conf bcc_celery.conf /etc/init

- Configure nginx:

    - Delete ``default`` site from ``/etc/nginx/sites-enabled``

            $ sudo rm /etc/nginx/sites-enabled/default

    - Create ``/etc/nginx/sites-available/bcc`` directory and copy ``bcc_nginx.conf``
    file from the BioCloudCentral repo there

            $ sudo mkdir /etc/nginx/sites-available/bcc
            $ sudo cp bcc_nginx.conf /etc/nginx/sites-available/bcc/

    - Create the following symlink

            $ sudo ln -s /etc/nginx/sites-available/bcc/bcc_nginx.conf /etc/nginx/sites-enabled/bcc

    - Optionally update the number of worker threads in ``/etc/nginx/nginx.conf``
    - Start ``sudo service nginx start`` or reload nginx: ``sudo nginx -s reload``

- Start the app services:

        $ sudo service bcc start
        $ sudo service bcc_celery start

- The app is now available at ``https://server.ip.address/``. The Admin part of
the app is available at ``https://server.ip.address/admin``.

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
