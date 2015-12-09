This is an all new version of Cloudlaunch currently being developed as per
[issue #49](https://github.com/galaxyproject/cloudlaunch/issues/49). Stay tuned.

## Install

Cloudlaunch is based on Python 3.5 and although it may work on older Python
versions, 3.5 is the only supported version.
Use of virtualenv is also highly advised.

    $ mkdir launcher && cd launcher
    $ virtualenv-3.4 .cl && source .cl/bin/activate
    $ git clone -b dev git@github.com:galaxyproject/cloudlaunch.git
    $ cd cloudlaunch
    $ pip install -r requirements.txt
    $ cd django-cloudlaunch
    $ python manage.py migrate
    $ python manage.py runserver
