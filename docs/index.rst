.. IETF BibXML service documentation master file, created by
   sphinx-quickstart on Sun Nov 21 16:58:14 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Overview
========

BibXML service provides access to citations
and a mechanism to read internal & external citation sources.
To understand how this service works,
it is recommended to read its API specification and explore GUI.
(If needed, see :doc:`set it up locally</howto/develop-locally>`.)

Below documentation aims to be relevant
to BibXML service maintainers, developers and operators.

.. seealso::

   - `BibXML project README <https://github.com/ietf-ribose/bibxml-project>`_
   - `RFP <https://www7.ietf.org/media/documents/BibXML_Service_RFP.pdf>`_

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   topics/index
   howto/index
   ref/index
   rfp-requirements
   evolution

Code layout
===========

.. parsed-literal::

   ├── README.rst
   │
   ├── static/
   │   │   Client-side CSS and JS.
   │   ├── css
   │   └── js
   │
   │   Post-processing client-side code:
   ├── package.json
   ├── package-lock.json
   ├── babel.config.json
   ├── postcss.config.js
   ├── tailwind.config.js
   ├── build/
   │       Directory where build artifacts end up.
   │
   ├── docs/
   │   ├── conf.py
   │   ├── index.rst
   │   │
   │   │   Building documentation HTML:
   │   ├── Dockerfile
   │   ├── docker-compose.yml
   │   ├── build/
   │   │       Where built documentation ends up.
   │   │
   │   ├── _static
   │   └── ...
   │
   ├── mypy.ini
   │       mypy linting/type-checking configuration.
   │
   │   Operations-related:
   ├── docker-compose.yml
   ├── docker-compose.dev.yml
   ├── Dockerfile
   ├── wait-for-migrations.sh
   ├── ops/
   │   │
   │   ├── db.Dockerfile
   │   ├── load-postgres-extensions.sh
   │   │
   │   ├── grafana-\*.yml
   │   │       Grafana data source and dashboard provisioning.
   │   ├── grafana-dashboard-\*.json
   │   │       Grafana dashboard configurations.
   │   │
   │   ├── prometheus-config.yml
   │   │       Prometheus configuration template.
   │   └── prometheus.Dockerfile
   │
   ├── requirements.txt
   │       Python requirements.
   │
   ├── manage.py
   │       Django project entry point.
   │
   ├── bibxml/
   │   │   Django project main module.
   │   │
   │   ├── settings.py
   │   │       Django settings.
   │   ├── urls.py
   │   │       Site URL configuration.
   │   ├── ...
   │   ├── asgi.py
   │   └── wsgi.py
   │
   ├── templates/
   │       General templates.
   │
   ├── bib_models/
   │       Bibliographic item dataclasses/Pydantic models.
   │
   ├── sources/
   │       Bibliographic data sources
   │
   ├── main/
   │   │   Retrieval GUI and API views and associated utilities.
   │   │
   │   ├── templates/
   │   │       Templates for browsing GUI.
   │   └── models.py
   │           Django model definitions for indexed bibliographic data.
   │
   ├── management/
   │   │   Management GUI and API views and associated utilities.
   │   │
   │   ├── templates/
   │   │       Templates for management GUI.
   │  ...
   │
   ├── datatracker/
   │       Datatracker integration: token validation, OAuth2.
   │
   ├── prometheus/
   │       Prometheus metrics & export view.
   │
   ├── doi/
   │   │   DOI retrieval implementation.
   │   │
   │   └── crossref.py
   │
   └── xml2rfc_compat/
   │       xml2rfc tools style API support.
   │
   └── common/
       ├── pydantic.py
       ├── query_profiler.py
       ├── git.py
       └── util.py


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
