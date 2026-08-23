"""The ops endpoint, and a check that the documented API surface is all there."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

EXPECTED_OPERATIONS = {
    ("get", "/health"),
    ("get", "/users"),
    ("post", "/auth/login"),
    ("post", "/auth/logout"),
    ("get", "/today"),
    ("get", "/days/{day}"),
    ("get", "/weeks"),
    ("get", "/months/{year}/{month}"),
    ("post", "/completions"),
    ("delete", "/completions"),
    ("post", "/completions/bonus"),
    ("get", "/me"),
    ("patch", "/me"),
    ("put", "/me/pin"),
    ("get", "/buckets"),
    ("post", "/buckets"),
    ("patch", "/buckets/{bucket_id}"),
    ("get", "/habits"),
    ("post", "/habits"),
    ("patch", "/habits/{habit_id}"),
    ("put", "/habits/{habit_id}/schedule"),
    ("post", "/habits/{habit_id}/archive"),
    ("patch", "/habits/reorder"),
}


def test_health_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_every_documented_endpoint_is_published() -> None:
    """The OpenAPI schema at /docs is the contract Phase 3 will build against."""
    spec = app.openapi()

    published = {
        (method, path)
        for path, operations in spec["paths"].items()
        for method in operations
    }

    assert EXPECTED_OPERATIONS <= published


def test_there_is_no_hard_delete_or_public_signup() -> None:
    """Two absences that are deliberate, not oversights."""
    spec = app.openapi()

    assert "delete" not in spec["paths"].get("/habits/{habit_id}", {})
    assert "delete" not in spec["paths"].get("/buckets/{bucket_id}", {})
    assert "post" not in spec["paths"].get("/users", {})
