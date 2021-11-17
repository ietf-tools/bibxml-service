==============
BibXML Service
==============

For an overview, see https://github.com/ietf-ribose/bibxml-project.

This project uses Docker, Django and PostgreSQL.


Running locally using Docker Desktop and Compose
------------------------------------------------

Ensure you are already running bibxml-indexer (see respective README).

Ensure shared configuration and access credentials
(e.g., PostgreSQL user and password)
are configured in the environment.

Then, run ``docker compose up`` from repository root.

To check successful deployment, check http://127.0.0.1:8000/api/v1/.


Credits
-------

Authored by Ribose as produced under the IETF BibXML SOW.
