========================
How to run in production
========================

.. todo:: Complete this section.


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


.. todo:: Document environment variables that matter with HTTPS.

.. todo:: CSP setup.


Monitoring errors
=================

The service can report to a Sentry instance.
It is recommended to provide ``SENTRY_DSN`` environment variable.
