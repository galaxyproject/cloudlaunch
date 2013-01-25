## Deploying BioCloudCentral with Apache via WSGI

Using [mod_wsgi][3], an Apache server can be configured to host
BioCloudCentral. The following template shows an example of a minimal
[vhost][1] configuration to enable this. The template configures the
`biocloudcentral` user host BioCloudCentral out of the directory
`/usr/share/biocloudcentral/project`. This templates requires a Python
2.7 virtualenv to have been setup according to the BioCloudCentral
documentation.

    <VirtualHost>
        ServerName SERVER_NAME # Replace with your server name

        WSGIDaemonProcess biocloudcentral user=biocloudcentral processes=2 threads=10 display-name=%{GROUP} python-path=/usr/share/biocloudcentral/project:/usr/share/biocloudcentral/project/lib/python2.7/site-packages
        WSGIProcessGroup biocloudcentral

        WSGIScriptAlias / /usr/share/biocloudcentral/project/biocloudcentral/wsgi.py

        DocumentRoot /usr/share/biocloudcentral/project
        Alias /static/admin/ /usr/share/biocloudcentral/project/lib/python2.7/site-packages/django/contrib/admin/media/
        Alias /static/ /usr/share/biocloudcentral/project/static/

        <Directory /usr/share/biocloudcentral/project/>
            Order allow,deny
            allow from all
        </Directory>

    </VirtualHost>

Warning: The cached session backend that is setup by default for
BioCloudCentral does not work when deployed in this manner. A
`biocloudcentral/settings_local.py` file with the following contents
to configure a compatible session engine:

    SESSION_ENGINE = "django.contrib.sessions.backends.db"

More information can be found [here][2]:

[1]: http://httpd.apache.org/docs/2.2/vhosts/
[2]: http://stackoverflow.com/questions/4421114/session-issue-with-djangoapachemod-wsgi
[3]: http://code.google.com/p/modwsgi/
