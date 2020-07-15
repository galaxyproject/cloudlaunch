Configure CloudLaunch with data
===============================

Once running, it is necessary to load the CloudLaunch database with information
about the appliances available for launching as well as cloud providers
where those appliances can be launched.

The following commands show how to load the information that is available on
the hosted CloudLaunch server available at https://launch.usegalaxy.org/. It
is recommended to load those values and then edit them to fit your needs.

Loading clouds
--------------

Appliances define properties required to properly launch an application on a
cloud provider. Run the following commands from the CloudLaunch server
repository with the suitable Conda environment activated.

.. code-block:: bash

    cd django-cloudlaunch
    curl https://raw.githubusercontent.com/CloudVE/cloudlaunch-helm/master/cloudlaunchserver/data/1_clouds.json --output clouds.json
    python manage.py loaddata clouds.json

If we start the CloudLaunch server now and naviage to the admin console,
``DJCLOUDBRIDGE -> Clouds``, we can see a list of cloud providers that have
been loaded and CloudLaunch can target.

If you would like to add a new cloud provider to be included in either the
hosted service or for distribution, please issuea pull requets to includ the
necessary connection properties to
https://github.com/CloudVE/cloudlaunch-helm/blob/master/cloudlaunchserver/data/1_clouds.json


Loading appliances
------------------

Rather than loading application-specific information by hand, we can load apps
from an application registry in bulk. At the moment, this action needs to be
performed from the CloudLaunch admin console.

On the CloudLaunch admin console, head to ``CloudLaunch -> Applications`` page
and click ``Add application`` button in the top right corner. Provide an
arbitrary name, say `placeholder`, for the application name and click save. Any
information provided for this application will get overwritten with the
information from the application reigistry. Back on the page listing
applications, select the checkbox next to the newly created application and
then from the ``Action`` menu, select ``Import app data from url``. Click
``Update`` on the next page to load the default set of applications and your
installation of CloudLaunch will have loaded all currenly available apps.
