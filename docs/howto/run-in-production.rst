========================
How to run in production
========================

There are many ways the service could be deployed.

Except for reliance on Docker, no assumptions are made about how infrastructure is operated.

That said, below is a **very simple** example of how it is possible to run the service
on AWS infrastructure using the bundled Compose configuration.

.. seealso:: :doc:`/topics/production-setup`

.. note::

   Below, 12345 is a sample port used for communicating with the origin. You can use any port, like 80.

1. Using AWS Lightsail, provision an Ubuntu x86-64 server with port 12345 open.

2. Assign a static IP to the instance. Take note of it.

3. Using AWS Route 53, point "origin.your.chosen.domain.name.com"
   to that static IP by creating an A record.

4. SSH into the server, install Docker and Docker Compose [1]_ [2]_ and enter a Tmux session.

5. Clone this repository under ``ubuntu`` user home directory.

6. Place a ``.env`` file at the root of the repository with following contents::

       DEBUG=0
       HOST=your.chosen.domain.name.com
       PORT=12345
       DB_NAME=bibxml
       DB_SECRET=random string
       DJANGO_SECRET=a very long and very random string
       API_SECRET=API secret to be used in management GUI and API authentication
       SERVICE_NAME=IETF BibXML service
       CONTACT_EMAIL=operating team contact email
       DATATRACKER_CLIENT_ID=Datatracker OAuth2 client ID
       DATATRACKER_CLIENT_SECRET=Datatracker OAuth2 client secret
       SOURCE_REPO_URL=https://github.com/ietf-ribose/bibxml-service
       SENTRY_DSN=your Sentry DSN string
       MATOMO_URL=Matomo URL
       MATOMO_SITE_ID=Matomo site ID

7. Run the command::

       sudo docker-compose build && sudo docker-compose -f docker-compose.yml up

   If you want to run the bundled monitoring services [3]_, this would be::

       sudo docker-compose build && sudo docker-compose -f docker-compose.yml -f docker-compose.monitor.yml up

8. Set up a CloudFront distribution that
   uses plain HTTP to talk to "origin.your.chosen.domain.name.com" via port 12345,
   responds to "your.chosen.domain.name.com" as an alternate domain name (CNAME),
   and redirects HTTP to HTTPS for visitors from the outside
   (you may need to provision an SSL certificate first).

9. Using Route 53, point "your.chosen.domain.name.com" to your CloudFront distribution
   by creating an alias record.

After CloudFront distribution is initialized,
the site should be available via https://your.chosen.domain.name.com.

.. [1] https://docs.docker.com/engine/install/ubuntu/

.. [2] https://docs.docker.com/compose/install/

.. [3] The bundled ``docker-compose.monitor.yml`` is there primarily for illustrative purposes,
       as typically you would already have a Prometheus instance set up.

       If you have a Prometheus instance, update it to scrape two additional targets:
       "origin.your.chosen.domain.name.com:9808" (Celery async task worker)
       and "origin.your.chosen.domain.name.com:12345" (web instance with Hypercorn web server).

       If you increase the number of web instances,
       make sure each target’s URL is added to your Prometheus instance for scraping.

Updating
========

Simply SSH back in, ``tmux attach``, stop Docker Compose,
run ``git pull --rebase`` and re-run the Compose command from step 7.
