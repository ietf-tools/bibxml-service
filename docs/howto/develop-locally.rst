======================
How to develop locally
======================

.. contents::
   :local:

Setting up
==========

You will need Docker and Docker Compose.
Configuration entry point lives in ``docker-compose.yml``
at the root of the repository.

.. note::

   For simplicity and consistency,
   in local development it’s recommended to use Docker & Docker Compose,
   and currently only that method is covered
   (the old-style conventional way of running under a venv isn’t).

   If you want to run this project directly,
   see :doc:`/ref/env` for environment variables,
   some of which are required by Django and need to be exported
   in your shell before you start the development server.

.. note::

   Commands below presume you use Docker Desktop with Docker Compose V2 support.

   - If you have installed Docker Compose separately under ``docker-compose`` binary,
     replace ``docker compose`` with ``docker-compose``.

   - Depending on your OS and installation method,
     you may also need to prepend Compose commands with ``sudo``.


Building base image
-------------------

.. note::

   Building base image is necessary both for running the service and building the docs,
   although full ``.env`` may not be strictly necessary if you only want to build the docs.

1. In repository root, create a file called ``.env`` with following contents:

   .. code-block:: text

      PORT=8000
      DB_NAME=bibxml
      DB_SECRET=qwert
      DJANGO_SECRET=FDJDSLJFHUDHJCTKLLLCMNII(****#TEFF
      HOST=localhost
      API_SECRET=test
      SERVICE_NAME=IETF BibXML service
      CONTACT_EMAIL=<ops contact email>
      DEBUG=1

   .. warning:: This environment is not suitable for production use.

   .. seealso::

      - :doc:`/ref/env`
      - `.env file syntax <https://docs.docker.com/compose/env-file/#syntax-rules>`_ in Compose documentation

2. In repository root, run ``docker compose build``.


Building documentation
----------------------

In production (without DEBUG and dev Compose config),
the documentation is made available under `/static/docs/index.html`.

To build & work on documentation locally, you need to take
a few more steps.

1. First, make sure to build the base image (see previous sections).

2. Under ``docs/``, run ``docker compose up``.

3. HTML documentation is served under ``localhost:8001``,
   and files are under ``docs/build/html``.

4. Documentation is continuously rebuilt whenever project files change,
   until you stop the container.


Running the service
===================

To simply serve the BibXML service, run ``docker compose up``.

Web front-end should be available under ``localhost:8000``.
API spec should be available under ``localhost:8000/api/v1``.

If you plan on making changes *and* you set DEBUG=1 in your environment,
for better development experience you can run the command this way instead::

    docker compose -f docker-compose.yml -f docker-compose.dev.yml up

This will mount source code directory and enable hot reload on changes.

If you want to run the service together with monitoring helper services,
run this::

    docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.monitor.yml up

.. seealso:: :doc:`/howto/run-in-production`


Monitoring logs
---------------

::

    docker compose logs -f -t


Invoking Django management commands
-----------------------------------

::

    docker compose exec web bash


Working on codebase
===================

Make sure to build and run the image as described in adjacent section.
Docker Compose will automatically reload the code for you.

In addition, make sure to build documentation,
make sure any new units are documented and all cross-references
(including the previously existing ones) resolve. Pay attention
to any new warnings during documentation generation, some warnings
are unavoidable but a new warning may indicate a broken cross-reference.

Linting
-------

The project includes a mypy configuration, and it’s crucial that every contributor
runs mypy to ensure valid typings.

Most IDEs can lint code on any change and highlight
problems in the editor.

.. important:: Always lint your code. Ideally, make your IDE do it by default.

Linting types properly requires mypy to be able to access imported modules.
However, this does not require running Docker at all times.
If on macOS or Linux, instead you can:

1. Create and active a Python 3.9 virtual environment using ``virtualenv``.
2. Install requirements with ``pip install -r requirements.txt``.
   (Don’t forget to repeat this step if requirements change later.)
3. Make sure your IDE resolves to Python within the virtualenv.
   In case of VS Code, use the “Select Python interpreter…” command.

.. note:: Some IDEs may require you to install mypy separately.

.. note::

   In VS Code, it’s recommended to disable mypy linting in Python extension
   and delegate linting to a separate Mypy extension. This ensures
   no third-party typing stubs are silently installed.

It’s also a good idea to run flake8. Where project conventions
differ from flake8 style, use project conventions.


Debugging
---------

The code can be debugged using an interactive tool such as ``ipdb``.
The environment is already setup to accept stdin interactions.

If you are running Docker using the command line, all you have to do is
install ``ipdb`` in your container::

    docker-compose exec web pip install ipdb

See the documentation [1]_ for more information.

.. [1]  https://pypi.org/project/ipdb/


Automated testing
-----------------

See :doc:`/howto/run-tests`.

Marking new release
-------------------

See :doc:`/howto/mark-releases`.
