#!/bin/sh
# wait-for-migrations.sh

set -e

python manage.py check --deploy || exit 1

until python manage.py migrate --check; do
  >&2 echo "Unapplied migrations in default DB might still exist: sleeping… $?"
  sleep 2
done

>&2 echo "Migrations in default DB applied: proceeding…"

exec "$@"
