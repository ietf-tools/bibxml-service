#!/bin/sh
set -e

echo "Waiting for test-db to initialize..."
wait-for-it db:5432 -- python manage.py test 2> /code/test-artifacts/stderr.log > /code/test-artifacts/stdout.log