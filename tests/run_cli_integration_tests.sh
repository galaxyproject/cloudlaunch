#!/bin/bash

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-cloudlaunchserver.settings_test}"
export CELERY_CONFIG_MODULE="${CELERY_CONFIG_MODULE:-cloudlaunchserver.celeryconfig_test}"
export CLOUDLAUNCH_SERVER_URL=http://localhost:8000/api/v1
export CLOUDLAUNCH_AUTH_TOKEN=272f075f152e59fd5ea55ca2d21728d2bfe37077

# Change working directory so everything is resolved relative to cloudlaunch root folder
SCRIPT_DIR=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd $SCRIPT_DIR/..

# Delete the existing database
rm -f /tmp/cloudlaunch_testdb.sqlite3

# Initialize database
python django-cloudlaunch/manage.py migrate

# Load initial test data
python django-cloudlaunch/manage.py loaddata tests/fixtures/initial_test_data.json

# Run cloudlaunch in background. Use noreload so that it runs in the same process as coverage
coverage run --source django-cloudlaunch --branch django-cloudlaunch/manage.py runserver --noreload &

# Wait for cloudlaunch to start
TIMEOUT=100
echo "Waiting for cloudlaunch to start..."
while ! nc -z localhost 8000; do
  if [[ $TIMEOUT -lt 0 ]]; then
        echo "Timeout waiting for cloudlaunch to start"
        exit 124
  fi
  sleep 0.1
  TIMEOUT=$((TIMEOUT-1))
done

# Clone temp cloudlaunch-cli repo
git clone https://github.com/CloudVE/cloudlaunch-cli /tmp/cloudlaunch-cli

# Run cloudlaunch-cli test suite against cloudlaunch
cd /tmp/cloudlaunch-cli/ && python setup.py test
# Cache return value of tests
ret_value=$?

# Kill the django process afterwards ($! is the last background process).
# There's a special SIGINT handler in manage.py that will terminate cloudlaunch
# gracefully, so coverage has a chance to write out its report
kill -SIGINT $!

exit $ret_value