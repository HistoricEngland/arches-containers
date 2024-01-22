try:
    from warden.settings import *
except ImportError:
    pass

import os
from django.core.exceptions import ImproperlyConfigured
import ast
import requests
import sys


def get_env_variable(var_name):
    msg = "Set the %s environment variable"
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = msg % var_name
        raise ImproperlyConfigured(error_msg)


def get_optional_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        return None


# options are either "PROD" or "DEV" (installing with Dev mode set gets you extra dependencies)
MODE = get_env_variable("DJANGO_MODE")

DEBUG = ast.literal_eval(get_env_variable("DJANGO_DEBUG"))

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": get_env_variable("PGDBNAME"),
        "USER": get_env_variable("PGUSERNAME"),
        "PASSWORD": get_env_variable("PGPASSWORD"),
        "HOST": get_env_variable("PGHOST"),
        "PORT": get_env_variable("PGPORT"),
        "POSTGIS_TEMPLATE": "template_postgis",
        "OPTIONS": {"sslmode": "prefer"},
    }
}

CELERY_BROKER_URL = "amqp://{}:{}@{}".format(
    get_env_variable("RABBITMQ_USER"), get_env_variable("RABBITMQ_PASS"), get_env_variable("RABBITMQ_HOST")
)  # RabbitMQ --> "amqp://guest:guest@localhost",  Redis --> "redis://localhost:6379/0"

# CANTALOUPE_HTTP_ENDPOINT = "http://{}:{}".format(get_env_variable("CANTALOUPE_HOST"), get_env_variable("CANTALOUPE_PORT"))

ELASTICSEARCH_HTTP_PORT = ast.literal_eval(get_env_variable("ESPORT"))
ELASTICSEARCH_HOSTS = [{"host": get_env_variable("ESHOST"), "port": ELASTICSEARCH_HTTP_PORT}]

## ES8
#ELASTICSEARCH_HOSTS = [{"scheme": "http", "host": get_env_variable("ESHOST"), "port": ELASTICSEARCH_HTTP_PORT}]

## USE ELASTIC CLOUD
#ELASTICSEARCH_CONNECTION_OPTIONS = {"cloud_id": get_env_variable("ELASTIC_CLOUD_ID"), "api_key": get_env_variable("ELASTIC_CLOUD_API_KEY")}

COUCHDB_URL = "http://{}:{}@{}:{}".format(
    get_env_variable("COUCHDB_USER"), get_env_variable("COUCHDB_PASS"), get_env_variable("COUCHDB_HOST"), get_env_variable("COUCHDB_PORT")
)  # defaults to localhost:5984

USER_ELASTICSEARCH_PREFIX = get_optional_env_variable("ELASTICSEARCH_PREFIX")
if USER_ELASTICSEARCH_PREFIX:
    ELASTICSEARCH_PREFIX = USER_ELASTICSEARCH_PREFIX



ALLOWED_HOSTS = get_env_variable("DOMAIN_NAMES").split()

USER_SECRET_KEY = get_optional_env_variable("DJANGO_SECRET_KEY")
if USER_SECRET_KEY:
    # Make this unique, and don't share it with anybody.
    SECRET_KEY = USER_SECRET_KEY

try:
    # dockerfile includes a static_root env variable
    STATIC_ROOT = get_env_variable("STATIC_ROOT")
except KeyError:
    STATIC_ROOT = f"/web_root/{get_env_variable('ARCHES_PROJECT')}/{get_env_variable('ARCHES_PROJECT')}/staticfiles/"

STATIC_URL = "/static/"


ARCHES_NAMESPACE_FOR_DATA_EXPORT = f"https://{get_env_variable('ARCHES_PROJECT')}:{get_env_variable('DJANGO_PORT')}"

AZURE_ACCOUNT_NAME = get_env_variable('AZURE_ACCOUNT_NAME')
AZURE_CONTAINER = get_env_variable('AZURE_CONTAINER')
AZURE_SAS_TOKEN = get_env_variable('AZURE_SAS_TOKEN')
AZURE_ACCOUNT_KEY = get_env_variable('AZURE_ACCOUNT_KEY')

COMPRESS_URL = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER}/"

