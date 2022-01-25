# syntax=docker/dockerfile:1
FROM python:3-slim

ENV PYTHONUNBUFFERED=1

RUN ["python", "-m", "pip", "install", "--upgrade", "pip"]

# Remove for non-slim image
RUN apt-get update && apt-get install -yq curl libpq-dev build-essential git

# We need to have both Python (for backend Django code)
# and Node (for Babel-based cross-browser frontend build).
# Starting with Python image and adding Node is simpler.
RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
  apt-get update && apt-get install -yq nodejs

COPY . /code
WORKDIR /code

RUN ["npm", "install"]
RUN ["pip", "install", "-r", "requirements.txt"]
RUN ["python", "manage.py", "collectstatic", "--noinput"]
RUN ["python", "manage.py", "compress"]
