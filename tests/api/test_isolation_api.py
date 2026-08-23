"""Boards are fully separate. This is the test that proves it over HTTP."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from tests.conftest import REFERENCE_MONDAY
from tests.test_scheduling import habit_named


def test_one_board_cannot_read_the_others_habits(
    client: TestClient, auth_b: dict[str, str], db: Session, user_a: User
) -> None:
    shower = habit_named(db, user_a, "Shower")

    response = client.patch(
        f"/habits/{shower.id}", headers=auth_b, json={"name": "Hijacked"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert shower.name == "Shower"


def test_one_board_cannot_tick_the_others_habits(
    client: TestClient, auth_a: dict[str, str], auth_b: dict[str, str], db: Session, user_a: User
) -> None:
    client.get("/today", headers=auth_a)
    shower = habit_named(db, user_a, "Shower")

    response = client.post(
        "/completions",
        headers=auth_b,
        json={"habit_id": shower.id, "date": REFERENCE_MONDAY.isoformat()},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_one_board_cannot_archive_the_others_habits(
    client: TestClient, auth_b: dict[str, str], db: Session, user_a: User
) -> None:
    shower = habit_named(db, user_a, "Shower")

    assert (
        client.post(f"/habits/{shower.id}/archive", headers=auth_b).status_code == 404
    )
    assert shower.active is True


def test_one_board_cannot_recolour_the_others_buckets(
    client: TestClient, auth_a: dict[str, str], auth_b: dict[str, str]
) -> None:
    target = client.get("/buckets", headers=auth_a).json()[0]["id"]

    response = client.patch(
        f"/buckets/{target}", headers=auth_b, json={"color_hex": "#000000"}
    )

    assert response.status_code == 404


def test_each_board_only_ever_sees_its_own_data(
    client: TestClient, auth_a: dict[str, str], auth_b: dict[str, str]
) -> None:
    board_a = client.get("/today", headers=auth_a).json()
    board_b = client.get("/today", headers=auth_b).json()

    assert board_a["active"]
    assert board_b["active"] == []
    assert client.get("/buckets", headers=auth_b).json() == []


def test_settings_changes_do_not_cross_boards(
    client: TestClient, auth_a: dict[str, str], auth_b: dict[str, str]
) -> None:
    client.patch("/me", headers=auth_b, json={"display_name": "Renamed B"})

    assert client.get("/me", headers=auth_a).json()["display_name"] == "User A"
    assert client.get("/me", headers=auth_b).json()["display_name"] == "Renamed B"
