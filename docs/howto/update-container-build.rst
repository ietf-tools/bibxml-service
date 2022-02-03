=============================
How to update container build
=============================

If you need to make changes that require changing some aspects
of container build, please follow this section.

Updating Dockerfile
===================

If you, for example, need to add some system requirements
or alter runtime environment, your changes may affect the Dockerfile.

Key points to remember if you update Dockerfile:

- Make equivalent changes to test.Dockerfile,
  and note if steps are expected to be different for Ubuntu.
- Update docker-compose file(s) used in development/testing
  if changes in Dockerfile affect how the image should be used by Compose.
