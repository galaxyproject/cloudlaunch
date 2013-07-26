#!/bin/bash
# Script used to start this app vi gunicorn. Before running the script,
# ensure the paths specified below are OK with your system

set -e
LOGFILE=/var/log/bcc_server.log
NUM_WORKERS=3
# User to run as
USER=`whoami`
# GROUP=`groups | cut -d' ' -f1`
# By default, BCC is assumed cloned in /gvl/bcc/
cd /gvl/bcc/biocloudcentral
# Activate the virtual env
source ../bin/activate
# Start the web app as a gunicorn-managed wsgi app
exec ../bin/gunicorn biocloudcentral.wsgi:application \
  -w $NUM_WORKERS \
  --user=$USER --log-level=debug \
  --log-file=$LOGFILE 2>>$LOGFILE \
  -b localhost:8000
