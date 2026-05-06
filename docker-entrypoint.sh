#!/bin/sh
set -e

mkdir -p "$(dirname "$DB_PATH")"

echo "Running migrations against $DB_PATH"
alembic upgrade head

exec "$@"
