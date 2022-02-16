.. IETF BibXML service documentation master file, created by
   sphinx-quickstart on Sun Nov 21 16:58:14 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Overview
========

BibXML service consumes bibliographic data sources and
provides web interfaces (API and GUI)
to query bibliographic data and to manage data source indexing.
It also provides bibliographic data accessible via xml2rfc tools style paths,
and provides a GUI to manage xml2rfc path resolution.
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

   topics/index
   howto/index
   ref/index
   evolution
   rfp-requirements


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Code layout
===========

.. parsed-literal::

   ├── README.rst
   │
   │
   │   Client-side code:
   │
   ├── static/
   │   ├── css
   │   └── js
   │
   │
   │   Post-processing client-side code:
   │
   ├── package.json
   ├── package-lock.json
   ├── babel.config.json
   ├── postcss.config.js
   ├── tailwind.config.js
   ├── build/
   │       Directory where build artifacts end up.
   │
   │
   │   Documentation:
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
   │
   │   Operations-related:
   │
   ├── docker-compose.yml
   ├── docker-compose.dev.yml
   ├── docker-compose.monitor.yml
   ├── Dockerfile
   ├── test.Dockerfile
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
   │
   │   Python project:
   │
   ├── requirements.txt
   │       Python requirements.
   │
   ├── mypy.ini
   │       mypy linting/type-checking configuration.
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
   │       Indexable sources. Async tasks, registry, etc.
   │
   ├── main/
   │   │   Retrieval GUI and API views and associated utilities.
   │   │
   │   ├── templates/
   │   │       Templates for browsing GUI.
   │   │
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
   │       Datatracker integration.
   │
   ├── doi/
   │   │   DOI retrieval, Crossref integration.
   │   │
   │   └── crossref.py
   │
   ├── prometheus/
   │       Prometheus metrics & export view.
   │
   └── xml2rfc_compat/
   │       xml2rfc tools API and format support.
   │
   └── common/
       ├── pydantic.py
       ├── query_profiler.py
       ├── git.py
       └── util.py
