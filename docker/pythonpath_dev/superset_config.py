# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# This file is included in the final Docker image and SHOULD be overridden when
# deploying the image to prod. Settings configured here are intended for use in local
# development environments. Also note that superset_config_docker.py is imported
# as a final step as a means to override "defaults" configured here
#
import logging
import os
from datetime import timedelta
from celery.schedules import crontab
from flask_caching.backends.filesystemcache import FileSystemCache
from redis import Redis

logger = logging.getLogger()

DATABASE_DIALECT = os.getenv("DATABASE_DIALECT")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_DB = os.getenv("DATABASE_DB")

EXAMPLES_USER = os.getenv("EXAMPLES_USER")
EXAMPLES_PASSWORD = os.getenv("EXAMPLES_PASSWORD")
EXAMPLES_HOST = os.getenv("EXAMPLES_HOST")
EXAMPLES_PORT = os.getenv("EXAMPLES_PORT")
EXAMPLES_DB = os.getenv("EXAMPLES_DB")

# The SQLAlchemy connection string.
SQLALCHEMY_DATABASE_URI = (
    f"{DATABASE_DIALECT}://"
    f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)

SQLALCHEMY_EXAMPLES_URI = (
    f"{DATABASE_DIALECT}://"
    f"{EXAMPLES_USER}:{EXAMPLES_PASSWORD}@"
    f"{EXAMPLES_HOST}:{EXAMPLES_PORT}/{EXAMPLES_DB}"
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_CELERY_DB = os.getenv("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.getenv("REDIS_RESULTS_DB", "0")

RESULTS_BACKEND = FileSystemCache("/app/superset_home/sqllab")

# Main Superset application cache configuration
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_cache_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
    "CACHE_REDIS_PASSWORD": REDIS_PASSWORD,
    # Connection pool settings
    'CACHE_REDIS_CONNECTION_POOL_SIZE': 50,  # Max number of connections
    'CACHE_REDIS_CONNECT_TIMEOUT': 10,       # Connection timeout in seconds
    'CACHE_REDIS_RETRY_ON_TIMEOUT': True,    # Retry on timeout
    'CACHE_REDIS_POOL_TIMEOUT': 30,          # Pool timeout
}

# Data cache for query results and dataset metadata
DATA_CACHE_CONFIG = {
    **CACHE_CONFIG,
    'CACHE_KEY_PREFIX': 'superset_data_',
}

# Dashboard filter state cache
FILTER_STATE_CACHE_CONFIG = {
    **CACHE_CONFIG,
    'CACHE_KEY_PREFIX': 'superset_filter_',
    'CACHE_DEFAULT_TIMEOUT': int(timedelta(days=90).total_seconds()),
    'REFRESH_TIMEOUT_ON_RETRIEVAL': True,
}

# Explore form data cache
EXPLORE_FORM_DATA_CACHE_CONFIG = {
    **CACHE_CONFIG,
    'CACHE_KEY_PREFIX': 'superset_explore_',
    'CACHE_DEFAULT_TIMEOUT': int(timedelta(days=7).total_seconds()),
    'REFRESH_TIMEOUT_ON_RETRIEVAL': True,
}

# Global async queries Redis configuration
GLOBAL_ASYNC_QUERIES_REDIS_CONFIG = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "db": REDIS_CELERY_DB,
    "ssl": False,
}
# Global async queries cache backend
GLOBAL_ASYNC_QUERIES_CACHE_BACKEND = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
    "CACHE_DEFAULT_TIMEOUT": 300,  # 5 minutes
    # Connection pool settings
    "CACHE_REDIS_CONNECTION_POOL_SIZE": 50,
    "CACHE_REDIS_CONNECT_TIMEOUT": 10,
    "CACHE_REDIS_RETRY_ON_TIMEOUT": True,
    "CACHE_REDIS_POOL_TIMEOUT": 30,
}


# Global async queries settings
GLOBAL_ASYNC_QUERIES_REDIS_STREAM_PREFIX = "async-events-"
GLOBAL_ASYNC_QUERIES_REDIS_STREAM_LIMIT = 1000
GLOBAL_ASYNC_QUERIES_REDIS_STREAM_LIMIT_FIREHOSE = 1000000
GLOBAL_ASYNC_QUERIES_JWT_COOKIE_NAME = "async-token"
GLOBAL_ASYNC_QUERIES_JWT_COOKIE_SECURE = True
GLOBAL_ASYNC_QUERIES_JWT_SECRET = os.getenv("GLOBAL_ASYNC_QUERIES_JWT_SECRET")
GLOBAL_ASYNC_QUERIES_TRANSPORT = "polling"  # Options: "polling" or "ws"
GLOBAL_ASYNC_QUERIES_POLLING_DELAY = int(timedelta(milliseconds=500).total_seconds() * 1000)


# Store cache keys in metadata DB for better cache management
STORE_CACHE_KEYS_IN_METADATA_DB = True


FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "GLOBAL_ASYNC_QUERIES": True,
    "DASHBOARD_RBAC": True,
    "ENABLE_ADVANCED_DATA_TYPES": True
}

class CeleryConfig:
    broker_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    imports = (
        "superset.sql_lab",
        "superset.tasks.scheduler",
        "superset.tasks.thumbnails",
        "superset.tasks.cache",
    )
    result_backend = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"

    # Celery settings
    worker_prefetch_multiplier = 1
    task_acks_late = True
    task_reject_on_worker_lost = True
    task_annotations = {
        'sql_lab.get_sql_results': {
            'rate_limit': '100/s'
        },
        'email_reports.send': {
            'rate_limit': '1/s'
        },
    }

    # Beat schedule for periodic tasks
    beat_schedule = {
        'reports.scheduler': {
            'task': 'reports.scheduler',
            'schedule': crontab(minute="*", hour="*"),  # Check for reports every minute
        },
        'reports.prune_log': {
            'task': 'reports.prune_log',
            'schedule': crontab(minute=10, hour=0),  # Daily log pruning
        },
    }


CELERY_CONFIG = CeleryConfig


#
# Optionally import superset_config_docker.py (which will have been included on
# the PYTHONPATH) in order to allow for local settings to be overridden
#
try:
    import superset_config_docker
    from superset_config_docker import *  # noqa

    logger.info(
        f"Loaded your Docker configuration at " f"[{superset_config_docker.__file__}]"
    )
except ImportError:
    logger.info("Using default Docker config...")

# Additional performance optimizations
SQLLAB_CTAS_NO_LIMIT = True
RESULTS_BACKEND_USE_MSGPACK = True  # Use MessagePack for serialization
SQL_MAX_ROW = 100000  # Maximum number of rows for queries
SQLLAB_ASYNC_TIME_LIMIT_SEC = int(timedelta(hours=6).total_seconds())  # 6 hours max query time

# App Name
APP_NAME = "Floww AI"

GUEST_ROLE_NAME= 'Gamma'
GUEST_TOKEN_JWT_SECRET = os.getenv("GUEST_TOKEN_JWT_SECRET")
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_HEADER_NAME = "X-GuestToken"
GUEST_TOKEN_JWT_EXP_SECONDS = 30 # 5 minutes

ENABLE_CORS = True

CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["*"],
    "origins": ["*"],
}

TALISMAN_ENABLED = False
HTTP_HEADERS={"X-Frame-Options":"ALLOWALL"}
ENABLE_PROXY_FIX = True
WTF_CSRF_ENABLED=False

FAB_ADD_SECURITY_API = True

SESSION_SERVER_SIDE = True
SESSION_TYPE = "redis"
SESSION_REDIS = Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_RESULTS_DB)
