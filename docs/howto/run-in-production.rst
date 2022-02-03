========================
How to run in production
========================

General setup
=============

Please refer to container reference bundled in the Compose configuration
(:doc:`/ref/containers`), which illustrates the way the service
is intended to be run.

HTTPS setup
===========

BibXML service is intended to be run
behind a load balancer (reverse proxy, CDN)
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
     that can result in stale bibliographic data being displayed.


Monitoring errors
=================

The service can report to a Sentry instance.
It is recommended to provide ``SENTRY_DSN`` environment variable.


Tracking metrics
================

Web service exports metrics in Prometheus format under ``/metrics/`` path.
The path requires HTTP Basic authentication (see :doc:`/topics/auth`).

Celery worker process also exports metrics under port 9080.


.. note::

   ``docker-compose.monitor.yml`` provides a configuration that runs
   Prometheus, Grafana, Flower and Celery exporter utility image::
   
       docker compose -f docker-compose.yml -f docker-compose.monitor.yml up
   
   .. seealso:: :doc:`/ref/containers`


Scaling
=======

It is possible to run multiple instances of the web service
by spinning multiple containers.

If you run multiple instances of the web container,
make sure the Prometheus instance is able to discover all scaled containers
and scrapes bibliographic data access and other metrics
from all of them.

.. important:: Do **not** increase the number of Hypercorn workers
               per instance. Prometheus Python client metric export,
               as implemented, will not work in multiprocessing scenarios.
               The supported method of scaling is via increasing

.. important:: Do **not** scale the number of async task workers
               (nor containers).
               Indexing tasks as currently implemented
               are not intended to be run in parallel.
