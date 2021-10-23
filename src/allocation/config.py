import os
from typing import Dict


def get_postgres_uri() -> str:
    host = os.environ.get("DB_HOST", "localhost")
    port = 5432
    password = os.environ.get("DB_PASSWORD", "abc123")
    user, db_name = "allocation", "allocation"
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_api_url() -> str:
    host = os.environ.get("API_HOST", "localhost")
    port = 5000
    return f"http://{host}:{port}"


def get_redis_host_and_port() -> Dict:
    host = os.environ.get("REDIS_HOST", "localhost")
    port = 6379
    return dict(host=host, port=port)


def get_email_host_and_port() -> Dict:
    host = os.environ.get("EMAIL_HOST", "localhost")
    port = 11025 if host == "localhost" else 1025
    http_port = 18025 if host == "localhost" else 8025
    return dict(host=host, port=port, http_port=http_port)


def get_dev_db_uri():
    return "sqlite:///dev_data.sqlite"
