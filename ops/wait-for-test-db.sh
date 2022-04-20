#!/bin/sh
set -e

wait-for-it db:5432 -- python manage.py test 2> /code/test-artifacts/stderr.log > /code/test-artifacts/stdout.log