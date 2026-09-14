# syntax=docker/dockerfile:1
FROM python:3.14-slim

# FROM lspcontainers/pyright-langserver

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

# Install requirements for building docs
RUN pip install sphinx

# Copy and install requirements separately to let Docker cache layers
COPY requirements.txt /code/requirements.txt
COPY package.json /code/package.json
COPY package-lock.json /code/package-lock.json

WORKDIR /code

RUN ["pip", "install", "-r", "requirements.txt"]

RUN npm install -g pyright

CMD ["pyright-langserver", "--stdio"]
