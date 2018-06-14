#!/bin/bash
cd "${0%/*}"/..

echo "Apply database migrations from `pwd`"
python manage.py migrate

echo "Load initial data from /app/initial_data/*.json"
python manage.py loaddata /app/initial_data/*.json

echo "Create a superuser"
cat scripts/create_superuser.py | python manage.py shell
