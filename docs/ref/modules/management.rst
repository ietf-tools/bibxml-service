==================================
``management`` — citation sourcing
==================================

.. contents::
   :local:

.. module:: management

``tasks`` — async task definition
============================================

.. module:: management.tasks

These tasks are run using Celery worker.

.. autofunction:: management.tasks._fetch_and_index

``repo`` — working with Git repositories
===================================================

.. automodule:: management.repo
   :members:

``index`` — reading sourced data into DB
===================================================

.. automodule:: management.index
   :members:
