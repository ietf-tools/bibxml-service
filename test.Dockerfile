# syntax=docker/dockerfile:1

# Meant to more or less follow
# the main ``Dockerfile``, except it’s based on Ubuntu
# because main image is based on Python image (and thus Debian)
# while Playwright only supports Ubuntu:
FROM ubuntu:focal

ENV PYTHONUNBUFFERED=1

# Install Python: part 1
RUN apt-get update
# The DEBIAN_FRONTEND suppresses tzinfo prompt (probably part of software-properties-common?)
RUN DEBIAN_FRONTEND=noninteractive apt-get install -yq curl libpq-dev git build-essential software-properties-common gcc
RUN add-apt-repository -y ppa:deadsnakes/ppa

# Install Node.
RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash -
RUN apt-get update
RUN apt-get install -yq nodejs

# Install Python: part 2 (depends on apt-get update made during Node install)
RUN apt-get install -y python3.10 python3.10-distutils python3.10-dev
RUN ln -sf python3.10 /bin/python
RUN ln -sf pip3 /bin/pip

RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

# TODO: Get rid of this
RUN ["python", "-m", "pip", "install", "--upgrade", "pip"]

# Install Playwright (required for tests only)
RUN ["pip", "install", "playwright"]
RUN ["python", "-m", "playwright", "install"]
RUN ["playwright", "install-deps"]

COPY requirements.txt /code/requirements.txt
COPY package.json /code/package.json
COPY package-lock.json /code/package-lock.json

WORKDIR /code

RUN ["pip", "install", "-r", "requirements.txt"]
RUN ["npm", "install"]

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


COPY . /code

RUN ["python", "manage.py", "collectstatic", "--noinput"]
RUN ["python", "manage.py", "compress"]

ENV WAIT_VERSION 2.7.2
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/$WAIT_VERSION/wait /wait
RUN chmod +x /wait

CMD python -m coverage run -m test 2> /code/test-artifacts/stderr.log > /code/test-artifacts/stdout.log && ./codecov
