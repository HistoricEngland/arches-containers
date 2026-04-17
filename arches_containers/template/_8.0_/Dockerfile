FROM he/{{project}}:dev_base
USER root

## Build Args
ARG PROJ_NAME={{project}}
ARG PROJ_REPO_NAME={{project_repo_directory}}
ARG ARCHES_PATH=./arches
ARG DOCKER_PATH=./docker

## copy and install the project
COPY ./${ARCHES_PROJECT_REPO_DIRECTORY} ${APP_ROOT}
WORKDIR ${APP_ROOT}
RUN pip install -e '.[dev]'
RUN rm -rf /root/.cache/pip/*

# Allow overwriting of settings and configuration files outside of base image.
WORKDIR ${WEB_ROOT}
COPY $DOCKER_PATH/settings_local.py ${WEB_ROOT}/docker/settings_local.py
COPY $DOCKER_PATH/conf.d ${WEB_ROOT}/docker/conf.d
COPY $DOCKER_PATH/supervisor.conf ${WEB_ROOT}/docker/supervisor.conf

# Set default workdir
WORKDIR ${WEB_ROOT}

# # Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["run_arches"]

# Expose port 8000
EXPOSE 8000