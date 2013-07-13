## BioCloudCentral

Easily launch [CloudMan][2] and [CloudBioLinux][3] platforms without
any configuration. You can use this directly on [biocloudcentral.org][7] or
run it locally - either way, it takes about 2 minutes to go from nothing to
a configured and scalable analysis platform on top of cloud resources.

### Development

This [Django][1] application deploys directly to [Heroku][4]. To run locally,
start by installing Python, PostgreSQL and [virtualenv][5]. When developing locally,
build a local virtualenv and install the dependencies:

    $ virtualenv --no-site-packages .
    $ source bin/activate
    $ pip install -r requirements.txt

Next, create a PostgreSQL database (remember to change the port, username, and password
as well as to match those to what you put into your [biocloudcentral/settings.py][6]),
apply the database migrations, and, optionally, preload your database with the AWS
information:

    $ sudo su postgres -c "psql --port #### -c \"CREATE ROLE afgane LOGIN CREATEDB PASSWORD 'password'\""
    $ createdb --username afgane --port #### biocloudcentral
    $ python biocloudcentral/manage.py syncdb
    $ python biocloudcentral/manage.py migrate biocloudcentral
    $ python biocloudcentral/manage.py loaddata biocloudcentral/aws_db_data.json

Finally, start the web server and the Celery workers (probably in two separate
tabs):

    $ python biocloudcentral/manage.py runserver
    $ python biocloudcentral/manage.py celeryd --concurrency 3 --loglevel=info

Use git to commit changes and push to Heroku for live deployment:

    $ git remote add heroku git@heroku.com:biocloudcentral.git
    $ git push heroku master

[1]: https://www.djangoproject.com/
[2]: http://usecloudman.org
[3]: http://cloudbiolinux.org
[4]: http://devcenter.heroku.com/articles/django
[5]: https://github.com/pypa/virtualenv
[6]: https://github.com/chapmanb/biocloudcentral/blob/master/biocloudcentral/settings.py
[7]: http://biocloudcentral.org

## LICENSE

The code is freely available under the [MIT license][l1].

[l1]: http://www.opensource.org/licenses/mit-license.html
