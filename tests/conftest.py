"""Shared pytest fixtures for tmf-mock tests."""
import pytest
from fastapi.testclient import TestClient
from tmf_mock.store import Store, set_store
from tmf_mock.server import create_app


@pytest.fixture
def store():
    s = Store()
    set_store(s)
    yield s


@pytest.fixture
def seeded_store():
    from tmf_mock.seed import seed_store
    s = Store()
    set_store(s)
    seed_store(s)
    yield s


@pytest.fixture
def client(store):
    app = create_app(seed=False)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded_client(seeded_store):
    app = create_app(seed=False)
    with TestClient(app) as c:
        yield c
