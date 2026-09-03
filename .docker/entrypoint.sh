#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput >/dev/null
python manage.py bootstrap_data

exec python manage.py runserver 0.0.0.0:8000
