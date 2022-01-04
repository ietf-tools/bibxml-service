==================================
``management`` — citation sourcing
==================================

.. todo:: Complete management module reference.

.. module:: management

.. contents::
   :local:

Sourcing logic
==============

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
