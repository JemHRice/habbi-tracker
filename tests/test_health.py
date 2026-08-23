"""The only HTTP surface Phase 1 exposes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_no_feature_endpoints_exist_yet() -> None:
    """Phase 1 stays in its lane: login/today/tick/week/month are Phase 2."""
    paths = {route.path for route in app.routes}

    assert "/health" in paths
    assert not {path for path in paths if path.startswith(("/today", "/habits", "/auth"))}
