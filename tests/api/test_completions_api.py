"""Ticking, un-ticking and bonuses over HTTP."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from tests.conftest import REFERENCE_MONDAY
from tests.test_scheduling import habit_named

YESTERDAY = REFERENCE_MONDAY - timedelta(days=1)
LOCKED_DAY = REFERENCE_MONDAY - timedelta(days=4)


def test_completing_returns_the_updated_today_view(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    client.get("/today", headers=auth_a)
    shower = habit_named(db, user_a, "Shower")

    response = client.post(
        "/completions",
        headers=auth_a,
        json={"habit_id": shower.id, "date": REFERENCE_MONDAY.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "today"
    assert body["done_count"] == 1
    assert [entry["habit"]["name"] for entry in body["completed"]] == ["Shower"]
    assert "Shower" not in {habit["name"] for habit in body["active"]}


def test_uncompleting_restores_the_habit(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    client.get("/today", headers=auth_a)
    shower = habit_named(db, user_a, "Shower")
    payload = {"habit_id": shower.id, "date": REFERENCE_MONDAY.isoformat()}

    client.post("/completions", headers=auth_a, json=payload)
    response = client.request("DELETE", "/completions", headers=auth_a, json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["done_count"] == 0
    assert body["completed"] == []
    assert "Shower" in {habit["name"] for habit in body["active"]}


def test_a_bonus_is_recorded_but_excluded_from_the_percentage(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    client.get("/today", headers=auth_a)
    laundry = habit_named(db, user_a, "Laundry")  # Wednesdays and Saturdays

    response = client.post(
        "/completions/bonus",
        headers=auth_a,
        json={"habit_id": laundry.id, "date": REFERENCE_MONDAY.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert [entry["habit"]["name"] for entry in body["bonuses"]] == ["Laundry"]
    assert body["done_count"] == 0
    assert body["daily_pct"] == 0.0
    assert "Laundry" not in {habit["name"] for habit in body["available_extras"]}


def test_completing_yesterday_returns_that_days_view(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    """Catching up yesterday should answer about yesterday, not about today."""
    client.get("/today", headers=auth_a)
    reading = habit_named(db, user_a, "Reading")

    response = client.post(
        "/completions",
        headers=auth_a,
        json={"habit_id": reading.id, "date": YESTERDAY.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "day"
    assert body["date"] == YESTERDAY.isoformat()
    assert [entry["habit"]["name"] for entry in body["completed"]] == ["Reading"]


def test_editing_a_locked_day_is_refused(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    client.get("/today", headers=auth_a)
    shower = habit_named(db, user_a, "Shower")

    response = client.post(
        "/completions",
        headers=auth_a,
        json={"habit_id": shower.id, "date": LOCKED_DAY.isoformat()},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EDIT_WINDOW_LOCKED"


def test_a_bonus_on_a_locked_day_is_refused(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    client.get("/today", headers=auth_a)
    laundry = habit_named(db, user_a, "Laundry")

    response = client.post(
        "/completions/bonus",
        headers=auth_a,
        json={"habit_id": laundry.id, "date": LOCKED_DAY.isoformat()},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EDIT_WINDOW_LOCKED"


def test_completing_an_unscheduled_habit_is_a_validation_error(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    """That is a bonus, not a completion — the two stay distinct."""
    client.get("/today", headers=auth_a)
    laundry = habit_named(db, user_a, "Laundry")

    response = client.post(
        "/completions",
        headers=auth_a,
        json={"habit_id": laundry.id, "date": REFERENCE_MONDAY.isoformat()},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION"


def test_a_bonus_on_a_scheduled_habit_is_a_validation_error(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    client.get("/today", headers=auth_a)
    shower = habit_named(db, user_a, "Shower")

    response = client.post(
        "/completions/bonus",
        headers=auth_a,
        json={"habit_id": shower.id, "date": REFERENCE_MONDAY.isoformat()},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION"


def test_an_unknown_habit_is_not_found(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.post(
        "/completions",
        headers=auth_a,
        json={"habit_id": 999999, "date": REFERENCE_MONDAY.isoformat()},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_a_missing_field_is_a_validation_error(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.post("/completions", headers=auth_a, json={"habit_id": 1})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"


def test_mutations_require_a_token(client: TestClient) -> None:
    response = client.post(
        "/completions", json={"habit_id": 1, "date": REFERENCE_MONDAY.isoformat()}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
