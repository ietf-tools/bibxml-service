RFP requirement compliance
==========================

1. Server-side is written in Python 3.9 with type annotations.

   Client-side JavaScript is purposefully maintained entirely
   optional for core functionality.
   Where provided, except for Matomo integration snippet, it uses
   the latest JavaScript syntax.

   Styling uses Tailwind CSS 3.

   Both CSS and JS are adjusted for cross-browser support
   as far as feasible on front-end compilation stage by transpiling
   via Babel/PostCSS (see also: :doc:`/howto/style-web-pages`).

   .. note::

      Using a reactive JSX-based framework was strongly considered. However,

      - a strong preference for Python and Django server-side was felt,
      - maintaining server-rendered HTML was considered a priority,
      - implementing JSX rendering in pure Python
        was deemed excessive for the circumstances,
      - rendering JSX server-side by calling Node from Python
        was considered brittle, and
      - deeply involving another framework in addition to Django
        would have complicated future maintenance and development
        by widening the expertise required from respective teams.

2. The service is based on Django 4,
   with a number of default contrib applications turned off.

   Development team believes that Django remains among the best-documented
   OSS projects.

3. .. todo:: Document rsync datastore

4. Ephemeral storage used by the service includes PostgreSQL and Redis.

   For long-term storage, Git repositories with Relaton-formatted
   (serialized to YAML) bibliographic data are used. Those sources are used
   to populate PostgreSQL database at runtime.

5. xml2rfc-style paths are supported, where requested path is used
   to construct a query against Relaton bibliographic item JSON,
   and obtained item is returned serialized in XML.

   Refer to :doc:`/topics/xml2rfc-compat` for details.

6. The service could be deployed behind a CDN.
   A CloudFront-based deployment had been tested in development environment.

   See :doc:`/howto/run-in-production` for specifics regarding HTTPS termination.

7. The service is delivered as a set of containers, of which the web frontend
   could be deployed in multiple concurrent instances behind a load balancer.

   Note that other containers (async task worker, PostgreSQL, Redis)
   must be deployed each in single instance only.

8. The service and associated data source and infrastructure repositories
   are hosted under https://github.com/ietf-ribose/.

9. .. todo:: Confirm this requirement is satisfied.

10. Build process is implemented as a GHA workflow
    with deployment triggered on each push to a tag:
    see :github:`.github/workflows/main.yml`.

11. API documentation is available as OpenAPI in YAML
    (under ``/openapi.yaml``, ``/openapi-legacy.yaml``),
    and in human-readable shape under ``/api/v1/`` and ``/api-spec/openapi_spec_main/``.

12. Matomo integration is supported
    via ``MATOMO_URL`` and either ``MATOMO_SITE_ID`` or ``MATOMO_CONTAINER``
    environment variables.

13. .. todo:: Confirm this point.

14. BibXML service does not aggregate access analytics itself,
    but facilitates it in following ways:

    - By exporting Prometheus counters for bibliographic item hits
      under ``/metrics/``, with the same Basic HTTP auth that applies to management GUI.

      As an example, the bundled Docker Compose runs a Prometheus instance
      that imports BibXML service metrics
      and a Grafana instance with two provisioned dashboards.

    - By reporting to Sentry, if ``SENTRY_DSN`` environment variable is configured correctly.
      Sentry’s main purpose is error tracking,
      but its performance dashboard allows to view requests by path.

    - By assigning a custom handler for ``api_access`` logger in ``settings.LOGGING``,
      directing individual access events to somewhere that is aggregated as desired.

      (Source code modification is required in this case.)

15. Requests to BibXML service API,
    except for xml2rfc-style paths, require a valid Datatracker bibxml token
    to be passed as ``X-Datatracker-Token`` HTTP header.

16. See :doc:`/howto/add-new-output-format`.
