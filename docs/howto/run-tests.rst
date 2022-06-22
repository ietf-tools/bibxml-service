================
How to run tests
================

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

