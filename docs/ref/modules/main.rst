=========================================
``main`` — citation retrieval API and GUI
=========================================

.. automodule:: main

.. contents::
   :local:

Helper types
============

.. automodule:: main.types
   :members:
   :show-inheritance:

Views
=====

.. module:: main.views

.. autofunction:: main.views.home

Browsing citations by :term:`document identifier`
-------------------------------------------------

.. autofunction:: main.views.browse_citation_by_docid

Utility/generic views
---------------------

.. automodule:: main.util
   :members:
   :show-inheritance:

Template tags
-------------

.. automodule:: main.templatetags.relaton
   :members:

Models
======

.. autoclass:: main.models.RefData
   :members:

``indexed``: querying sourced citations
=======================================

.. automodule:: main.indexed
   :members:

.. autoexception:: main.exceptions.RefNotFoundError

``external``: querying external citation sources
================================================

.. automodule:: main.external
   :members:
