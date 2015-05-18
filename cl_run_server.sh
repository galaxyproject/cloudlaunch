#!/bin/bash
# Script used to start this app vi gunicorn. Before running the script,
# ensure the paths specified below are OK with your system

set -e
LOGFILE=/var/log/cl_server.log
NUM_WORKERS=3
# User to run as
USER=`whoami`
# GROUP=`groups | cut -d' ' -f1`
# By default, CL is assumed cloned within `/srv/cloudlaunch`
INSTALL_DIR="/srv/cloudlaunch"
cd "$INSTALL_DIR/cloudlaunch"
# Activate the virtual env
source "$INSTALL_DIR/.cl/bin/activate"
# Start the web app as a gunicorn-managed wsgi app
exec ../bin/gunicorn biocloudcentral.wsgi:application \
  -w $NUM_WORKERS \
  --user=$USER --log-level=debug \
  --log-file=$LOGFILE 2>>$LOGFILE \
  -b localhost:8000
