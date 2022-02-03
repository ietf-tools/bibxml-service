================
How to run tests
================

::

    docker compose -f docker-compose.test.yml up

Note that this will build a different Docker image
than the one used for live project.
See ``test.Dockerfile`` for details.
