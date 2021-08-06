import time
import pytest
import requests

# from pathlib import Path
from sqlalchemy import create_engine

# from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import clear_mappers, sessionmaker

from adapters.orm import metadata, start_mappers
import config


@pytest.fixture(scope="session")
def dev_db():
    engine = create_engine(config.get_dev_db_uri())
    metadata.create_all(engine)
    return engine


@pytest.fixture
def dev_session(dev_db):
    start_mappers()
    yield sessionmaker(bind=dev_db)()
    clear_mappers()


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite://")
    metadata.create_all(engine)
    return engine


@pytest.fixture
def session(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db)()
    clear_mappers()


@pytest.fixture
def session_factory(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db)
    clear_mappers()


# def wait_for_postgres_to_come_up(engine):
#     deadline = time.time() + 10
#     while time.time() < deadline:
#         try:
#             return engine.connect()
#         except OperationalError:
#             time.sleep(0.5)
#     pytest.fail("postgres never came up")


# @pytest.fixture("session")
# def postgres_db():
#     engine = create_engine(config.get_postgres_uri())
#     wait_for_postgres_to_come_up(engine=engine)
#     metadata.create_all(engine)
#     yield engine
#     metadata.drop_all()


# @pytest.fixture
# def pg_session(postgres_db):
#     start_mappers()
#     yield sessionmaker(bind=postgres_db)()
#     clear_mappers()


def wait_for_webapp_to_come_up():
    deadline = time.time() + 10
    url = config.get_api_url()
    while time.time() < deadline:
        try:
            return requests.get(url)
        except ConnectionError:
            time.sleep(0.5)
    pytest.fail("API never came up")


@pytest.fixture
def restart_api():
    wait_for_webapp_to_come_up()
