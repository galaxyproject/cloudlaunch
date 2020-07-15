.. cloudlaunch documentation master file, created by
   sphinx-quickstart on Mon Dec 18 16:10:21 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the CloudLaunch developer documentation
==================================================

CloudLaunch is a ReSTful, extensible Django app for discovering and launching
applications on cloud, container, or local infrastructure. A live version is
available at https://launch.usegalaxy.org/.

CloudLaunch can be extended with your own plug-ins which can provide custom
launch logic for arbitrary custom applications. Visit the live site to see
currently available applications in the Catalog. CloudLaunch is also tightly
integrated with `CloudBridge <github.com/gvlproject/cloudbridge>`_, which makes
CloudLaunch natively multi-cloud.

CloudLaunch has a web and commandline front-end. The Web UI is maintained in the
`CloudLaunch-UI <https://github.com/galaxyproject/cloudlaunch-ui>`_ repository.
The commandline client is maintained in the
`cloudlaunch-cli <https://github.com/CloudVE/cloudlaunch-cli>`_ repository.

Installation
------------

The recommended method for installing CloudLaunch is via the
`CloudLaunch Helm chart <topics/production_server_mgmt.html>`_.

To install a development version, take a look at
`development installation page <topics/development_server_installation.html>`_.


Application Configuration
-------------------------

Once the application components are installed and running (regardless of the
method utilized), it is necessary to load appliance and cloud provider
connection properties. See `this page <topics/configuration.html>`_ for how to
do this.

Authentication Configuration
----------------------------

User authentication to CloudLaunch should be managed via social auth. For
development purposes, it is possible to use Django authentication in which
case simply creating a superuser is sufficient. If you intend on having users
of your CloudLaunch installation, you will want to configure
`social auth <topics/social_auth.html>`_.


Table of contents
-----------------
.. toctree::
   :maxdepth: 1

   topics/overview.rst
   topics/production_server_mgmt.rst
   topics/development_server_installation.rst
   topics/configuration.rst
   topics/social_auth.rst
