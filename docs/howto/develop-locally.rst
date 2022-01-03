====================================
Set up local development environment
====================================

You will need Docker Desktop with Compose V2 support enabled.

1. In repository root, create file ``.env`` with following contents::

       PORT=8000
       DB_NAME=indexer
       DB_SECRET=qwert
       DJANGO_SECRET="FDJDSLJFHUDHJCTKLLLCMNII(****#TEFF"
       HOST=localhost
       API_SECRET="test"
       DEBUG=1

   .. seealso:: :doc:`/ref/env`

2. In repository root, run ``docker compose up``.

3. Web front-end should be available under ``localhost:8000``.


Building documentation
======================

1. Under ``docs/``, run ``docker compose up``.

2. Documentation is built in HTML under ``docs/build/html``,
   and is rebuilt on file changes until you stop the container.

3. Documentation will also be served under ``localhost:8001``.
