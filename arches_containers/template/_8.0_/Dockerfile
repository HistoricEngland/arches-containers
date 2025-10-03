FROM python:3.13-slim-bookworm
USER root

## Build Args
ARG PROJ_NAME=project
ARG ARCHES_PATH=./arches
ARG DOCKER_PATH=./docker

## Setting default environment variables
ENV ARCHES_PROJECT=$PROJ_NAME
ENV WEB_ROOT=/web_root
ENV APP_ROOT=${WEB_ROOT}/${ARCHES_PROJECT}
ENV PKG_ROOT=${APP_ROOT}_package
ENV DATA_ROOT=${APP_ROOT}_data
# Root project folder
ENV ARCHES_ROOT=${WEB_ROOT}/arches
ENV WHEELS=/wheels
ENV PYTHONUNBUFFERED=1
ENV NODE_VERSION=20.14.0

# Get the pre-built python wheels from the build environment
RUN mkdir ${WEB_ROOT}
RUN mkdir ${PKG_ROOT}
RUN mkdir ${DATA_ROOT}

# Set up PostgreSQL APT repository with modern GPG keyring method
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates lsb-release gnupg git \
  && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
  && apt-get update -y

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        make \
        software-properties-common \
        build-essential \
        mime-support \
        libgdal-dev \
        postgresql-client-14 \
        dos2unix \
        wait-for-it \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# nvm environment variables
ENV NVM_DIR=/usr/local/nvm
RUN mkdir $NVM_DIR

# install nvm
# https://github.com/nvm-sh/nvm#install-script
RUN curl --silent -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.4/install.sh | bash -

# install node and npm
RUN . $NVM_DIR/nvm.sh \
    && nvm install $NODE_VERSION \
    && nvm alias default $NODE_VERSION \
    && nvm use default

# add node and npm to path so the commands are available
ENV NODE_PATH=$NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH=$NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

# Install the Arches application
# FIXME: ADD from github repository instead?
COPY $ARCHES_PATH ${ARCHES_ROOT}
RUN chmod +x ${ARCHES_ROOT}/arches/install/arches_admin.py

# From here, run commands from ARCHES_ROOT
WORKDIR ${ARCHES_ROOT}

RUN pip install --upgrade pip setuptools wheel
RUN pip install -e '.[dev]'
RUN rm -rf /root/.cache/pip/*


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