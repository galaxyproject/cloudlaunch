## BioCloudCentral

Easily launch [CloudBioLinux][3], [CloudMan][2] and [Galaxy][8] platforms without
any configuration. You can use this app directly on [biocloudcentral.org][7] or
run it locally - either way, it takes about 2 minutes to go from nothing to
a configured cluster-in-the-cloud and a scalable analysis platform on top of
cloud resources.

### Installing

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

If you are deploying to a production server, you'll want to use [PostgreSQL][15].
If not already installed, do so and then create a database (remember to change the
password and match it to what you put into your [biocloudcentral/settings.py][6]
file).

    $ sudo su postgres -c "psql --port 5432 -c \"CREATE ROLE bcc LOGIN CREATEDB PASSWORD 'password'\""
    $ createdb --username bcc --port 5432 biocloudcentral

Finally, apply the database migrations, and, optionally, preload your database
with the details about [AWS instances][9]:

    $ python biocloudcentral/manage.py syncdb
    $ python biocloudcentral/manage.py migrate biocloudcentral
    $ python biocloudcentral/manage.py migrate djcelery
    $ python biocloudcentral/manage.py migrate kombu.transport.django
    $ python biocloudcentral/manage.py loaddata biocloudcentral/aws_db_data.json

### Deploying locally

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
