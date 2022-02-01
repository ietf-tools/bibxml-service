FROM alpine:latest

RUN apk add --update --no-cache gettext

COPY prometheus-config.yml /tmp/prometheus-template.yml

ARG TARGET_HOSTS
ARG HTTP_BASIC_USERNAME
ARG HTTP_BASIC_PASSWORD
ARG JOB_NAME

ENV TARGET_HOSTS=$TARGET_HOSTS
ENV HTTP_BASIC_USERNAME=$HTTP_BASIC_USERNAME
ENV HTTP_BASIC_PASSWORD=$HTTP_BASIC_PASSWORD
ENV JOB_NAME=$JOB_NAME

RUN envsubst < /tmp/prometheus-template.yml > /prometheus.yml

RUN echo /prometheus.yml

FROM prom/prometheus:latest
COPY --from=0 /prometheus.yml /etc/prometheus/prometheus.yml
