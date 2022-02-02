==================================
``management`` — citation sourcing
==================================

.. module:: management

.. contents::
   :local:

Sourcing logic
==============

``datasets`` — source discovery
-------------------------------

.. automodule:: management.datasets
   :members:

``repo`` — working with Git repositories
----------------------------------------

.. automodule:: management.repo
   :members:

``index`` — reading sourced data into DB
----------------------------------------

.. automodule:: management.index
   :members:

Working with async tasks
========================

``tasks`` — async task definition
---------------------------------

.. module:: management.tasks

These tasks are run using Celery worker.

.. autofunction:: management.tasks._fetch_and_index

``task_status`` — monitoring tasks
----------------------------------

.. automodule:: management.task_status
   :members:

``celery`` — Celery interface
-----------------------------

.. automodule:: management.celery
   :members:

Interface
=========

Management GUI
--------------

.. automodule:: management.views
   :members:

Management API
--------------

.. automodule:: management.api
   :members:

Authentication
--------------

.. automodule:: management.auth
   :members:
