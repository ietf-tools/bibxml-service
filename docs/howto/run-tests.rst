================
How to run tests
================

::

    docker compose -f docker-compose.test.yml up --exit-code-from test

The ``--exit-code-from`` flag will stop all
the containers after the tests are completed.

Note that this will build a different Docker image
than the one used for live project.
See ``test.Dockerfile`` for details.
