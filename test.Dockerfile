# syntax=docker/dockerfile:1
FROM python:3.10-slim@sha256:502f6626d909ab4ce182d85fcaeb5f73cf93fcb4e4a5456e83380f7b146b12d3
# FROM python:3.11-rc-slim -- no lxml wheel yet

RUN ["python", "-m", "pip", "install", "--upgrade", "pip"]

# Could probably be removed for non-slim Python image
RUN apt-get update && apt-get install -yq curl libpq-dev build-essential git

# To build lxml from source, need at least this (but maybe better stick to wheels):
# RUN apt-get install -yq libxml2-dev zlib1g-dev libxslt-dev

# Copy and install requirements separately to let Docker cache layers
COPY requirements.txt /code/requirements.txt

# Install Coverage (required for tests only)
RUN ["pip", "install", "coverage"]

WORKDIR /code

RUN ["pip", "install", "-r", "requirements.txt"]

# Provide default test environment
ENV SNAPSHOT=test
ENV SERVICE_NAME="BibXML test"
ENV DB_NAME=test
ENV DB_USER=test
ENV DB_SECRET=test
ENV DB_HOST=test-db
ENV DJANGO_SECRET="IRE()dA(*EFW&*RHIUWEJFOUHSVSJO(ER*#U#(JRIAELFKJfLAJFIFJ(JOSIERJO$IFUHOI()#*JRIU"
ENV PRIMARY_HOSTNAME=test.local
ENV REDIS_HOST=test-redis
ENV REDIS_PORT=6379
ENV CONTACT_EMAIL="example@ribose.com"
ENV API_SECRET=test

# Copy the rest of the codebase
COPY . /code

#RUN ["python", "manage.py", "collectstatic", "--noinput"]
#RUN ["python", "manage.py", "compress"]

ENV WAIT_VERSION 2.7.2
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/$WAIT_VERSION/wait /wait
RUN chmod +x /wait

RUN curl -Os https://uploader.codecov.io/latest/linux/codecov
RUN chmod +x codecov

CMD python -m coverage run manage.py test 2> /code/test-artifacts/stderr.log > /code/test-artifacts/stdout.log && ./codecov -t ${CODECOV_TOKEN}
