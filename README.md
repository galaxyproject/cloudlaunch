## BioCloudCentral

Easily launch [CloudMan][2] and [CloudBioLinux][3] enabled machines without
any configuration.

### Development

This [Django][1] application deploys directly to [Heroku][4]. To run locally,
start by installing Python and [virtualenv][5]. When developing locally,
build a local virtualenv, install the dependencies and start the server:

    $ virtualenv --no-site-packages .
    $ source bin/activate
    $ pip install -r requirements.txt
    $ python biocloudcentral/manage.py runserver

Use git to commit changes and push to Heroku for live deployment:

    $ git remote add heroku git@heroku.com:biocloudcentral.git
    $ git push heroku master

[1]: https://www.djangoproject.com/
[2]: http://wiki.g2.bx.psu.edu/Admin/Cloud
[3]: http://cloudbiolinux.org
[4]: http://devcenter.heroku.com/articles/django
[5]: https://github.com/pypa/virtualenv
