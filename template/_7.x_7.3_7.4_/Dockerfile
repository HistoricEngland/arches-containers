FROM python:3.9.15
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

RUN apt-get update && apt-get install -y make software-properties-common

# Get the pre-built python wheels from the build environment
RUN mkdir ${WEB_ROOT}
RUN mkdir ${APP_ROOT}
RUN mkdir ${PKG_ROOT}
RUN mkdir ${DATA_ROOT}

# Install packages required to run Arches
# Note that the ubuntu/debian package for libgdal1-dev pulls in libgdal1i, which is built
# with everything enabled, and so, it has a huge amount of dependancies (everything that GDAL
# support, directly and indirectly pulling in mysql-common, odbc, jp2, perl! ... )
# a minimised build of GDAL could remove several hundred MB from the container layer.
RUN set -ex \
  && RUN_DEPS=" \
  build-essential \
  mime-support \
  libgdal-dev \
  postgresql-client-14 \
  dos2unix \
  " \
  && apt-get install -y --no-install-recommends curl \
  && curl -sL https://deb.nodesource.com/setup_14.x | bash - \
  && curl -sL https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
  && add-apt-repository "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -sc)-pgdg main" \
  && apt-get update -y \
  && apt-get install -y --no-install-recommends $RUN_DEPS \
  && apt-get install -y nodejs \
  && npm install -g yarn

RUN rm -rf /root/.cache/pip/*

# Install the Arches application
# FIXME: ADD from github repository instead?
COPY $ARCHES_PATH ${ARCHES_ROOT}
RUN chmod +x ${ARCHES_ROOT}/arches/install/arches-project

# From here, run commands from ARCHES_ROOT
WORKDIR ${ARCHES_ROOT}

RUN pip install --upgrade pip setuptools wheel
RUN pip install -e . --user --no-use-pep517 && pip install -r arches/install/requirements_dev.txt

COPY $DOCKER_PATH/entrypoint.sh /entrypoint.sh
RUN chmod -R 700 /entrypoint.sh &&\
  dos2unix /entrypoint.sh

WORKDIR ${WEB_ROOT}
RUN mkdir docker
COPY $DOCKER_PATH/settings_docker.py ${WEB_ROOT}/docker/settings_docker.py
COPY $DOCKER_PATH/conf.d ${WEB_ROOT}/docker/conf.d
COPY $DOCKER_PATH/supervisor.conf ${WEB_ROOT}/docker/supervisor.conf

RUN pip install supervisor
RUN mkdir /var/log/supervisor
RUN mkdir /var/log/celery

# Set default workdir
WORKDIR ${APP_ROOT}

# # Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["run_arches"]

# Expose port 8000
EXPOSE 8000