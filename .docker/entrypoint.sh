#!/bin/sh
set -e

python manage.py migrate
python manage.py seed --refresh || true
python manage.py collectstatic --noinput || true

exec python manage.py runserver 0.0.0.0:8000
