#!/bin/sh
# wait-for-migrations.sh

set -e

until python manage.py migrate --check; do
  >&2 echo "Unapplied migrations in default DB might still exist: sleeping… $?"
  sleep 2
done

>&2 echo "Migrations in default DB applied: proceeding…"

until python manage.py migrate --database index --check; do
  >&2 echo "Unapplied migrations in index DB might still exist: sleeping… $?"
  sleep 2
done

>&2 echo "Migrations in index DB applied: proceeding…"

exec "$@"
