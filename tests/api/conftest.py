"""Fixtures for the endpoint tests.

The app is built per test with its database dependency pointed at the same
rolled-back session the Phase 1 tests use, and the clock frozen at a fixed
moment — so timezone behaviour, the edit window and session expiry are all
deterministic over HTTP too.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import clock
from app.api import throttle
from app.api.deps import get_db
from app.main import create_app
from app.models import User
from tests.conftest import PIN_A, PIN_B, REFERENCE_MONDAY, local_moment

API_NOW = local_moment(REFERENCE_MONDAY, hour=9)
"""09:00 on a known Monday, in the seeded users' timezone."""


@pytest.fixture(autouse=True)
def _reset_throttle() -> Iterator[None]:
    """PIN throttle state is process-global; no test may leak into another."""
    throttle.reset_all()
    yield
    throttle.reset_all()


@pytest.fixture
def now() -> Iterator[datetime]:
    """Freeze the clock for the whole test, requests included."""
    with clock.frozen_time(API_NOW) as moment:
        yield moment


@pytest.fixture
def client(db: Session, now: datetime) -> Iterator[TestClient]:
    """A test client whose requests run against the test session."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client: TestClient, user: User, pin: str) -> str:
    """Log in and return the session token."""
    response = client.post("/auth/login", json={"user_id": user.id, "pin": pin})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth_header(token: str) -> dict[str, str]:
    """Build the Bearer header for a token."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_a(client: TestClient, user_a: User) -> dict[str, str]:
    """Authorization header for the full board."""
    return auth_header(login(client, user_a, PIN_A))


@pytest.fixture
def auth_b(client: TestClient, user_b: User) -> dict[str, str]:
    """Authorization header for the empty board."""
    return auth_header(login(client, user_b, PIN_B))
