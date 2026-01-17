#!/bin/sh
set -e

cd /app

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Collecting static..."
python manage.py collectstatic --noinput

echo "Seeding demo data (idempotent)..."
python manage.py seed_demo || true

echo "Starting gunicorn..."
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
