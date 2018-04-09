#!/bin/bash

SCRIPT_DIR=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

# Change working directory so everything is resolved relative to cloudlaunch root folder
cd $SCRIPT_DIR/..

# Initialize database
python django-cloudlaunch/manage.py migrate

# Load initial test data
python django-cloudlaunch/manage.py loaddata tests/fixtures/cloudlaunch_initial_test_data.json

# Run cloudlaunch in background. Use noreload so that it runs in the same process as coverage
coverage run --source django-cloudlaunch --branch django-cloudlaunch/manage.py runserver --noreload &

# Clone temp cloudlaunch-cli repo
git clone https://github.com/CloudVE/cloudlaunch-cli /tmp/cloudlaunch-cli

# Run cloudlaunch-cli test suite
(cd /tmp/cloudlaunch-cli/ && python setup.py test)

# Kill the django process afterwards ($! is the last background process).
# There's a special SIGINT handler in manage.py that will terminate cloudlaunch
# gracefully, so coverage has a chance to write out its report
kill -SIGINT $!

# Delete temp cloudlaunch-cli repo
sudo rm -r /tmp/cloudlaunch-cli
