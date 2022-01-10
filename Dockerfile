# syntax=docker/dockerfile:1
FROM python:3

ENV PYTHONUNBUFFERED=1

ARG SNAPSHOT_HASH
ARG SNAPSHOT_TIME
ENV SNAPSHOT_HASH=$SNAPSHOT_HASH
ENV SNAPSHOT_TIME=$SNAPSHOT_TIME

# We need to have both Python (for backend Django code)
# and Node (for Babel-based cross-browser frontend build).
# Starting with Python image and adding Node is simpler.

RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
  apt-get update && apt-get install -yq nodejs

COPY . /code
WORKDIR /code

RUN ["python", "-m", "pip", "install", "--upgrade", "pip"]
RUN ["pip", "install", "-r", "requirements.txt"]
RUN ["npm", "install"]
