#!/bin/sh
set -e

python manage.py migrate
python manage.py seed --refresh || true

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --reload
