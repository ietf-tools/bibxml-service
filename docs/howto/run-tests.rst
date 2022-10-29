================
How to run tests
================

Production/CI
-------------

::

    docker compose -f docker-compose.test.yml up --build --exit-code-from test

The ``--exit-code-from`` flag will automatically stop
all the containers after the tests are completed.

Tests are integrated as part as a Github Action workflow (CI).
Successfully running the tests will produce a coverage report.
This report will be available as a comment in every PR pointing
at the main branch.

.. note::

   This will build a different Docker image than the one used
   for live project. See ``test.Dockerfile`` for details.

.. note::

   If a valid CODECOV_TOKEN is provided as environment variable, the
   report will be uploaded to CodeCov. CODECOV_TOKEN should only be
   provided in the CI environment.

Locally
-------

Tests can be run locally without the need of having
a Codecov configuration. We can do so using the
following command:

::

    docker-compose exec web python manage.py test


.. note::

   In order to be able to execute this command,
   the whole environment needs to be up and running
   (.. seealso:: :doc:`/howto/develop-locally`).
