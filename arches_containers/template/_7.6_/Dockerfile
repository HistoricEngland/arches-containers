FROM he/{{project}}:dev_base
USER root

## Build Args
ARG PROJ_NAME=project
ARG DOCKER_PATH=./docker

## copy and install the project
COPY ./${PROJ_NAME} ${APP_ROOT}
WORKDIR ${APP_ROOT}
RUN pip install -e '.[dev]'
RUN rm -rf /root/.cache/pip/*

# Allow overwriting of settings and configuration files outside of base image.
WORKDIR ${WEB_ROOT}
COPY $DOCKER_PATH/entrypoint.sh /entrypoint.sh
RUN chmod -R 700 /entrypoint.sh && \
  dos2unix /entrypoint.sh

WORKDIR ${WEB_ROOT}
RUN mkdir docker
COPY $DOCKER_PATH/settings_local.py ${WEB_ROOT}/docker/settings_local.py
COPY $DOCKER_PATH/conf.d ${WEB_ROOT}/docker/conf.d
COPY $DOCKER_PATH/supervisor.conf ${WEB_ROOT}/docker/supervisor.conf

RUN pip install supervisor
RUN mkdir /var/log/supervisor
RUN mkdir /var/log/celery

# Set default workdir
WORKDIR ${WEB_ROOT}

# # Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["run_arches"]

# Expose port 8000
EXPOSE 8000