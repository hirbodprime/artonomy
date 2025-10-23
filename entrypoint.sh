#!/usr/bin/env bash
set -e

# Wait for Postgres if present
if [ "$DB_ENGINE" = "postgresql" ]; then
  echo "Waiting for postgres at $DB_HOST:$DB_PORT..."
  until python -c "import socket; s=socket.socket(); s.connect(('$DB_HOST', int('$DB_PORT')))" 2>/dev/null; do
    sleep 1
  done
fi

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Start Gunicorn in prod mode; use runserver for dev compose file
if [ "${DJANGO_DEBUG,,}" = "true" ]; then
  python manage.py runserver 0.0.0.0:$PORT
else
  exec gunicorn your_project.wsgi:application --bind 0.0.0.0:$PORT --workers 3
fi
