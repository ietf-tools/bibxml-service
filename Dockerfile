# syntax=docker/dockerfile:1
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1

ARG SNAPSHOT
ENV SNAPSHOT=$SNAPSHOT

RUN ["python", "-m", "pip", "install", "--upgrade", "pip"]

# Could probably be removed for non-slim Python image
RUN apt-get update && apt-get install -yq curl libpq-dev build-essential git

# To build lxml from source, need at least this (but maybe better stick to wheels):
# RUN apt-get install -yq libxml2-dev zlib1g-dev libxslt-dev

# Install Node.
# We need to have both Python (for backend Django code)
# and Node (for Babel-based cross-browser frontend build).
# Starting with Python image and adding Node is simpler.
RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash -
RUN apt-get update
RUN apt-get install -yq nodejs

RUN apt-get clean && rm -rf /var/lib/apt/lists/

# Install requirements for building docs
RUN pip install sphinx

# Copy and install requirements separately to let Docker cache layers
COPY requirements.txt /code/requirements.txt
COPY package.json /code/package.json
COPY package-lock.json /code/package-lock.json

WORKDIR /code

RUN ["pip", "install", "-r", "requirements.txt"]
RUN ["npm", "install"]

# Copy the rest of the codebase
COPY . /code

RUN mkdir -p /code/build/static

RUN ["python", "manage.py", "collectstatic", "--noinput"]
RUN ["python", "manage.py", "compress"]

# Build docs
RUN sphinx-build -a -E -n -v -b html /code/docs/ /code/build/static/docs
