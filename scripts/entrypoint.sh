#!/bin/sh
# scripts/entrypoint.sh
# ──────────────────────
# Container startup script:
#   1. Wait for PostgreSQL to be ready
#   2. Run Django migrations
#   3. Start Gunicorn

set -e

echo "⏳  Waiting for PostgreSQL..."
until python -c "
import sys, os
import psycopg2
try:
    psycopg2.connect(os.environ.get('DATABASE_URL', ''))
    print('PostgreSQL is ready.')
except psycopg2.OperationalError:
    sys.exit(1)
"; do
    echo "  PostgreSQL unavailable — retrying in 2s"
    sleep 2
done

echo "🔄  Running database migrations..."
python manage.py migrate --noinput

echo "🚀  Starting Gunicorn..."
exec gunicorn finance_backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --worker-connections 1000 \
    --timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
