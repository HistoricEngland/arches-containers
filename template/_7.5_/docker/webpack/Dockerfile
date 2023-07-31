FROM python:3.10.12
USER root

ARG ARCHES_PATH=./arches
ARG DOCKER_PATH=./docker

ENV WEB_ROOT=/web_root
ENV APP_ROOT=${WEB_ROOT}/v75test
ENV ARCHES_ROOT=${WEB_ROOT}/arches
RUN mkdir -p ${APP_ROOT}/v75test/webpack

RUN apt-get update && apt-get install -y make software-properties-common
RUN set -ex \
  && apt-get update -y \
  && RUN_DEPS=" \
  build-essential \
  mime-support \
  libgdal-dev \
  dos2unix \
  git \
  " \
  && apt-get install -y --no-install-recommends curl \
  && apt-get install -y --no-install-recommends $RUN_DEPS

COPY $ARCHES_PATH ${ARCHES_ROOT}
# From here, run commands from APP_ROOT
WORKDIR ${APP_ROOT}

# nvm environment variables
ENV NVM_DIR /usr/local/nvm
RUN mkdir $NVM_DIR

ENV NODE_VERSION 16.20.1

# install nvm
# https://github.com/nvm-sh/nvm#install-script
RUN curl --silent -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.4/install.sh | bash -

# install node and npm
RUN echo "source $NVM_DIR/nvm.sh \
    && nvm install $NODE_VERSION \
    && nvm alias default $NODE_VERSION \
    && nvm use default" | bash -

# add node and npm to path so the commands are available
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

RUN npm install -g yarn && apt install wait-for-it


# From here, run commands from ARCHES_ROOT
WORKDIR ${ARCHES_ROOT}
RUN pip install -e . --user --no-use-pep517 && pip install -r arches/install/requirements.txt && pip install -r arches/install/requirements_dev.txt
COPY $DOCKER_PATH/webpack/entrypoint.sh ${WEB_ROOT}/entrypoint.sh
RUN chmod -R 700 ${WEB_ROOT}/entrypoint.sh
WORKDIR ${WEB_ROOT}
ENTRYPOINT [ "./entrypoint.sh" ]
CMD ["run_webpack"]
EXPOSE 8021