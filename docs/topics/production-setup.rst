================
Production setup
================

.. seealso:: :rfp:req:`6`

.. seealso::

   - The bundled Compose configuration
     :doc:`configures containers </ref/containers>`
     to illustrate the way the service is intended to be operated.

   - The :doc:`/howto/run-in-production`
     describes a basic example of production setup.


Environment
===========

The service requires
certain :doc:`environment variables </ref/env>`
to be available at runtime.

If you run via Compose, environment can be provided via ``.env`` file
as a sibling of ``docker-compose.yml``.

.. warning:: No matter how you provide environment variables,
             make sure ``DEBUG`` is **not** set in production.


HTTPS setup
===========

The service relies on being accessed via HTTPS URLs.

It is expected to be run from behind a load balancer (reverse proxy, CDN)
that terminates SSL and talks to BibXML in plain HTTP.

Typical choices include an Nginx frontend,
AWS CloudFront/ELB, CloudFlare.

.. important::

   - Make sure the connection between TLS-terminating layer
     and BibXML is secure.

     For example, in case of AWS-based infrastructure,
     there is a difference between terminating SSL at CloudFront or ELB
     where the latter is more secure (but more resource-intensive).

   - Make sure HTTP ``Host`` header and ``X-Forwarded-For`` headers
     are forwarded accurately to BibXML service.

   - Be minfdul of additional caching at LB/front-end proxy level
     that can result in stale bibliographic data being displayed,
     and for access metrics not being counted.

   - If you use the server-side Prometheus metric export mechanisms,
     your CDN configuration should let
     every resource request that matters metrics-wise
     hit the web application itself.

.. note::

   Django’s ``request.is_secure()`` convenience function may return
   a false negative if you terminate TLS outside of the service.


Monitoring errors
=================

The service can report to a Sentry instance.
It is recommended to provide ``SENTRY_DSN`` environment variable.


.. _tracking-metrics:

Tracking metrics
================

Web service exports metrics in Prometheus format under ``/metrics/`` path.
The path requires HTTP Basic authentication (see :doc:`/topics/auth`).

Celery worker process also exports metrics under port 9080.

.. _metrics-and-cdn:

.. warning::

   If you implement aggressive caching for all GET requests
   (e.g., on CDN level), exported metrics **will not be correct**
   and you should use metrics provided by your caching layer instead.

   For GUI/API hits to be counted correctly, caching for GET requests
   must be very selective.
   You can cache static assets and some pages,
   but requests to resources that matter for metric collection
   must hit the web application—if, for example,
   CDN short-circuits and returns cached result,
   the metric will not be incremented by server-side logic.

   These are probably the only paths
   to which GET requests can be cached safely:

   - ``/static/*`` (static assets such as CSS and JavaScript)
   - ``/about`` (about page, hits currently not counted)

.. note::

   ``docker-compose.monitor.yml`` provides a configuration that runs
   Prometheus, Grafana, Flower and Celery exporter utility image::

       docker compose -f docker-compose.yml -f docker-compose.monitor.yml up

   .. seealso:: :ref:`monitoring-containers` in bundled container reference


Scaling
=======

The web service
---------------

It is possible to run multiple instances of the web service
(the container that runs Hypercorn server)
by spinning up multiple containers.

.. warning:: Do **not** increase the number of Hypercorn workers
             per instance. Prometheus Python client metric export,
             as implemented, will not work in multiprocessing scenarios.
             Run multiple containers instead, if needed.

.. important::

   If you do run multiple instances of the web container,
   make sure each instance is added as a target for Prometheus,
   so that Prometheus scrapes complete bibliographic data access
   and other metrics. Otherwise, metrics will undercount.
   (This is currently not handled by the bundled Compose configuration.)

Other services
--------------

Other services are not intended to be run in parallel.
I.e., there should be at most 1 instance of each container
(DB, Celery async task processor, and so on).

.. warning:: Do **not** scale the number of async task workers
             within the Celery container, either.
             Indexing tasks, as currently implemented,
             are not intended to be run in parallel.
