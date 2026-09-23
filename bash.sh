#!/usr/bin/env bash
# Exit on error
set -o errexit

# Run database migrations
python manage.py makemigrations
python manage.py migrate

# Start the Gunicorn server
# Replace config.wsgi with your project's WSGI path if different
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
