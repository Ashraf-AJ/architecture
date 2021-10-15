import pytest
import requests
import shutil
import subprocess

# from pathlib import Path
import redis
from tenacity import retry, stop_after_delay
from sqlalchemy import create_engine

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import clear_mappers, sessionmaker

from allocation.adapters.orm import metadata, start_mappers
from allocation import config


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite://")
    metadata.drop_all(engine)
    metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db)
    clear_mappers()


@pytest.fixture
def session(session_factory):
    return session_factory()


@retry(stop=stop_after_delay(10))
def wait_for_postgres_to_come_up(engine):
    return engine.connect()


@pytest.fixture(scope="session")
def postgres_db():
    engine = create_engine(config.get_postgres_uri())
    wait_for_postgres_to_come_up(engine=engine)
    metadata.drop_all(engine)
    metadata.create_all(engine)
    return engine


@pytest.fixture
def pg_session_factory(postgres_db):
    start_mappers()
    yield sessionmaker(bind=postgres_db)
    clear_mappers()


@pytest.fixture
def pg_session(pg_session_factory):
    return pg_session_factory()


@retry(stop=stop_after_delay(10))
def wait_for_webapp_to_come_up():
    return requests.get(config.get_api_url())


@pytest.fixture
def restart_api():
    wait_for_webapp_to_come_up()


@retry(stop=stop_after_delay(10))
def wait_for_redis_to_come_up():
    r = redis.Redis(**config.get_redis_host_and_port())
    return r.ping()


@pytest.fixture
def restart_redis_pubsub():
    wait_for_redis_to_come_up()
    if shutil.which("docker-compose"):
        print("skipping restart, assumes running in container.")
        return
    subprocess.run(
        ["docker-compose", "restart", "-t", "0", "redis_pubsub"],
        check=True,
    )
