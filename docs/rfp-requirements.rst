RFP requirement compliance
==========================

.. contents::
   :local:

.. rfp:req::
   :id: 1

       The service must be written in Python 3 for the application code
       and Javascript/HTML/CSS for the interactive web page,
       built on modern infrastructure components and designed for maintainability.

   - Server-side is written in Python 3.9 with type annotations.

   - Client-side, JavaScript is purposefully maintained entirely
     optional for core functionality.
     Where provided, except for Matomo integration snippet, it uses
     the latest JavaScript syntax.

     Styling is based on Tailwind CSS 3.

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

   - Both CSS and JS are adjusted for cross-browser support
     as far as feasible on front-end compilation stage by transpiling
     via Babel/PostCSS. This allows to use the latest version of JS and CSS
     syntax for better legibility and maintainability.

   - Service is delivered with Dockerfile and Docker Compose specifications,
     which ensure development and production environment consistency
     and encapsulate required libraries.

   .. seealso:: :doc:`/ref/containers`, :doc:`/howto/style-web-pages`

.. rfp:req::
   :id: 2

       The new service must use a high quality, reliable, well maintained,
       well documented and actively supported web services/microservices framework.
       The IETF uses Django as its web framework
       but is open to the use of different frameworks for this RFP.

   The service is based on Django 4,
   with a number of default contrib applications turned off.

   Development team believes that Django remains among the best-documented
   OSS projects.

.. rfp:req::
   :id: 3

       The interface to the datastore suitable as the source for an rsync server
       must support the common Linux rsync service.
       This rsync service will be configured and maintained by the IETF.

   .. todo:: Confirm specifics

   The service does not currently expose data using rsync,
   but source data used by the service is available
   via repositories named after ``relaton-data-*`` pattern
   within https://github.com/ietf-ribose/.

   .. seealso:: :mod:`main.sources` for Relaton source implementation

.. rfp:req::
   :id: 4

       If the new service is to use a database then that must be PostgreSQL.

   Ephemeral storage used by the service :doc:`includes </ref/containers>`
   PostgreSQL and Redis.

   For long-term storage, Git repositories with Relaton-formatted
   (serialized to YAML) bibliographic data are used, and service
   populates PostgreSQL database at runtime by :term:`indexing <indexable source>` them.

.. rfp:req::
   :id: 5

       The service must maintain the following backward compatibility
       with the existing service:

       1. URL structure and file naming of the current web service.
          For example /public/rfc/bibxml/reference.RFC.7991.xml.
          This will allow existing tools to quickly shift to using the new service.
       2. For certain datasets (detailed below) the service must support
          a ‘live’ file name, which always serves the latest version
          of an XML citation at the time of retrieval,
          while also supporting the serving of specific versions. For example::

              reference.I-D.ietf-stir-passport-rcd.xml

          will return the XML citation for the current version of draft-ietf-stir-passport-rcd
          at the time of the request, while::

              draft-ietf-stir-passport-rcd-09.xml

          will always return the XML citation for version -09 of the Internet-Draft.

   xml2rfc-style paths are supported. Requested path is used
   to construct a query against Relaton bibliographic item JSON,
   and obtained item is returned serialized in XML.

   A manual map to a document identifier, if present,
   overrides automatic resolution.

   Fallback to data indexed from xml2rfc mirror Git repository
   is used as last resort.

   .. seealso::

      - :doc:`/topics/xml2rfc-compat` for xml2rfc compatibility overview
      - :data:`xml2rfc_compat.models.dir_subpath_regex` for path regular expression

.. rfp:req::
   :id: 6

       The service should assume deployment behind a CDN. Our current CDN is Cloudflare.

   The service could be deployed behind a CDN.
   A CloudFront-based deployment had been tested in development environment.

   See :doc:`/howto/run-in-production` for specifics regarding HTTPS termination.

.. rfp:req::
   :id: 7

       While we anticipate deploying this service as a single instance,
       it should be able to be deployed as a distributed service using cloud infrastructure providers.

   The service is delivered as a set of :doc:`containers </ref/containers>`,
   of which the web frontend
   could be deployed in multiple concurrent instances behind a load balancer.

   The simplest way to run it is to bring up a virtual instance
   (for example, AWS Lightsail) and run the provided Compose configuration.
   A scaling option can be provided for the “web” service if needed.
   A more complex setup would be to use something like EKS to manage containers
   (not covered by documentation).

   Note that containers other than “web” (such as async task worker, PostgreSQL, Redis, etc.)
   must be deployed each in single instance only.

.. rfp:req::
   :id: 8

       Development must use a public github repository under the IETF Tools Organisation

   The service and associated data source and infrastructure repositories
   are hosted under https://github.com/ietf-ribose/.

.. rfp:req::
   :id: 9

       All developed code must be supplied with ownership assigned to the IETF Trust
       and licensed under the IETF Trust specified open source license

   .. todo:: Confirm this requirement is satisfied.

.. rfp:req::
   :id: 10

       Early on in the development a build process must be added such that commits to the repository
       will build an image and run tests in a container based on that image,
       and when tests pass, will deploy a container on a staging site. 
       The image will be made available on a hub (such as hub.docker.com).
       We expect the same image to be useful for both production and development use.
       We anticipate a CD system that will allow us to deploy to potentially distributed
       production instances automatically on release as well.

   Build process is implemented as a GHA workflow
   with deployment triggered on each push to a tag:
   see :github:`.github/workflows/main.yml`.

.. rfp:req::
   :id: 11

       Design of the APIs, including full feature definition will be part of the project.

   API documentation is available as OpenAPI in YAML
   (under ``/openapi.yaml``, ``/openapi-legacy.yaml``),
   rendered as human-readable HTML under ``/api/v1/`` and ``/api-spec/openapi_spec_main/``.

.. rfp:req::
   :id: 12

       The interactive web page must support the inclusion scripts needed
       to support the Matomo web analytics tool.

   Matomo integration is supported
   via ``MATOMO_URL`` and either ``MATOMO_SITE_ID`` or ``MATOMO_CONTAINER``
   environment variables.

   .. seealso:: :ref:`Matomo environment variable reference <matomo-integration-env>`
                and :data:`bibxml.settings.MATOMO`

.. rfp:req::
   :id: 13

       If the new service is to include a rewrite of doilit rather than using the existing code,
       then this should be clearly stated in the RFP response.

   .. todo:: Confirm this point.

.. rfp:req::
   :id: 14

       The logging must include, at a minimum counts of accesses to each XML citation
       through the XML URLs, counts of accesses through the API, counts of accesses via rsync.

   BibXML service does not aggregate access analytics itself,
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

   .. seealso:: :mod:`prometheus.metrics` for exported metric declaration.

.. rfp:req::
   :id: 15

       The APIs will require the use of Datatracker-generated API tokens.
       Individuals will use personal API tokens generated from their accounts page.
       The Datatracker will provide an interface for validating tokens.
       Systems using the private APIs will use administratively provisioned tokens.
       The web service will allow anonymous access and will allow the user
       to log in using Datatracker credentials via OIDC.
       At this time, there is no expected difference in behavior for the website
       if the user is logged in or anonymous.

   Requests to BibXML service API,
   except for xml2rfc-style paths, require a valid Datatracker bibxml token
   to be passed as ``X-Datatracker-Token`` HTTP header.

   Datatracker OAuth2/OIDC flows are integrated in no-op mode.

   .. seealso:: :mod:`datatracker` for Python module reference.

.. rfp:req::
   :id: 16

       We anticipate adding additional output reference formats in the future, such as BibTex or CSL.
       The design of the service must facilitate the addition of these future formats.

   This service supports pluggable output formats for bibliographic data
   via a registry of ``BibliographicItem`` serializers.
   Bibliographic item details GUI and API automatically support
   serializers that were registered at service startup time.

   .. seealso::

      - :doc:`/howto/add-new-output-format`
      - :mod:`bib_models.serializers` for serializer registry Python reference
      - BibXML is registered as a pluggable serialization format
        in :mod:`xml2rfc_compat.serializer`.
