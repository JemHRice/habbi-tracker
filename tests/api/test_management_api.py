"""Habit and bucket management, and the two rules it must not work around."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from tests.conftest import REFERENCE_MONDAY
from tests.test_scheduling import habit_named


def bucket_id(client: TestClient, headers: dict[str, str], name: str) -> int:
    """Find one of the user's buckets by name."""
    buckets = client.get("/buckets", headers=headers).json()
    return next(bucket["id"] for bucket in buckets if bucket["name"] == name)


# --- Buckets --------------------------------------------------------------


def test_buckets_are_listed_in_order(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.get("/buckets", headers=auth_a)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 8
    assert [bucket["sort_order"] for bucket in body] == sorted(
        bucket["sort_order"] for bucket in body
    )
    assert body[0]["name"] == "Self-care"


def test_a_bucket_can_be_created(client: TestClient, auth_a: dict[str, str]) -> None:
    response = client.post(
        "/buckets",
        headers=auth_a,
        json={"name": "Garden", "color_hex": "#6C6C2C", "sort_order": 9},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Garden"
    assert len(client.get("/buckets", headers=auth_a).json()) == 9


def test_a_bucket_can_be_renamed_and_recoloured(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    target = bucket_id(client, auth_a, "Social")

    response = client.patch(
        f"/buckets/{target}", headers=auth_a, json={"color_hex": "#CA758A"}
    )

    assert response.status_code == 200
    assert response.json()["color_hex"] == "#CA758A"
    assert response.json()["name"] == "Social"  # untouched by a partial update


def test_a_malformed_colour_is_rejected(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.post(
        "/buckets", headers=auth_a, json={"name": "Nope", "color_hex": "red"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"


# --- Habits ---------------------------------------------------------------


def test_habits_are_listed_with_their_schedules(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.get("/habits", headers=auth_a)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 29
    laundry = next(habit for habit in body if habit["name"] == "Laundry")
    assert laundry["weekdays"] == [2, 5]
    assert laundry["active"] is True


def test_a_habit_can_be_created_and_appears_on_the_board(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.post(
        "/habits",
        headers=auth_a,
        json={
            "bucket_id": bucket_id(client, auth_a, "Health"),
            "name": "Stretch",
            "target_per_week": 7,
            "weekdays": [0, 1, 2, 3, 4, 5, 6],
            "sort_order": 30,
            "time_cap_minutes": 10,
        },
    )

    assert response.status_code == 201
    assert response.json()["weekdays"] == [0, 1, 2, 3, 4, 5, 6]
    assert "Stretch" in {
        habit["name"] for habit in client.get("/habits", headers=auth_a).json()
    }
    assert "Stretch" in {
        habit["name"] for habit in client.get("/today", headers=auth_a).json()["active"]
    }


def test_creating_a_habit_in_someone_elses_bucket_is_not_found(
    client: TestClient, auth_a: dict[str, str], auth_b: dict[str, str]
) -> None:
    response = client.post(
        "/habits",
        headers=auth_b,
        json={
            "bucket_id": bucket_id(client, auth_a, "Health"),
            "name": "Sneaky",
            "target_per_week": 1,
            "weekdays": [0],
            "sort_order": 1,
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_a_habit_can_be_edited(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    reading = habit_named(db, user_a, "Reading")

    response = client.patch(
        f"/habits/{reading.id}", headers=auth_a, json={"name": "Read a book"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Read a book"
    assert response.json()["time_cap_minutes"] == 20  # untouched


def test_a_time_cap_can_be_removed(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    """A null means "leave alone", so clearing needs its own flag."""
    reading = habit_named(db, user_a, "Reading")

    response = client.patch(
        f"/habits/{reading.id}", headers=auth_a, json={"clear_time_cap": True}
    )

    assert response.json()["time_cap_minutes"] is None


def test_a_schedule_can_be_replaced(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    laundry = habit_named(db, user_a, "Laundry")

    response = client.put(
        f"/habits/{laundry.id}/schedule", headers=auth_a, json={"weekdays": [0, 3]}
    )

    assert response.status_code == 200
    assert response.json()["weekdays"] == [0, 3]


def test_an_invalid_weekday_is_rejected(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    laundry = habit_named(db, user_a, "Laundry")

    response = client.put(
        f"/habits/{laundry.id}/schedule", headers=auth_a, json={"weekdays": [0, 9]}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"


def test_rescheduling_does_not_reshape_an_already_materialised_day(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    """Forward-only: today was already written, so today keeps its rows."""
    before = client.get("/today", headers=auth_a).json()
    shower = habit_named(db, user_a, "Shower")

    client.put(
        f"/habits/{shower.id}/schedule", headers=auth_a, json={"weekdays": [6]}
    )

    after = client.get("/today", headers=auth_a).json()
    assert "Shower" in {habit["name"] for habit in after["active"]}
    assert after["remaining_count"] == before["remaining_count"]


def test_archiving_hides_a_habit_but_keeps_its_history(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    client.get("/today", headers=auth_a)
    shower = habit_named(db, user_a, "Shower")
    client.post(
        "/completions",
        headers=auth_a,
        json={"habit_id": shower.id, "date": REFERENCE_MONDAY.isoformat()},
    )

    response = client.post(f"/habits/{shower.id}/archive", headers=auth_a)

    assert response.status_code == 200
    assert response.json()["active"] is False
    assert response.json()["archived_at"] is not None

    listed = {habit["name"] for habit in client.get("/habits", headers=auth_a).json()}
    assert "Shower" not in listed

    with_archived = client.get(
        "/habits", headers=auth_a, params={"include_archived": True}
    ).json()
    assert "Shower" in {habit["name"] for habit in with_archived}

    month = client.get("/months/2026/3", headers=auth_a).json()
    shower_row = next(row for row in month["habits"] if row["name"] == "Shower")
    assert shower_row["completed_days"] == 1


def test_there_is_no_hard_delete(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    shower = habit_named(db, user_a, "Shower")

    assert client.delete(f"/habits/{shower.id}", headers=auth_a).status_code == 405


def test_archiving_twice_is_harmless(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    shower = habit_named(db, user_a, "Shower")

    client.post(f"/habits/{shower.id}/archive", headers=auth_a)
    response = client.post(f"/habits/{shower.id}/archive", headers=auth_a)

    assert response.status_code == 200
    assert response.json()["active"] is False


def test_habits_can_be_reordered_in_a_batch(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    shower = habit_named(db, user_a, "Shower")  # position 4
    water = habit_named(db, user_a, "Morning water")  # position 1

    response = client.patch(
        "/habits/reorder",
        headers=auth_a,
        json=[
            {"habit_id": shower.id, "sort_order": 1},
            {"habit_id": water.id, "sort_order": 4},
        ],
    )

    assert response.status_code == 200
    listed = client.get("/habits", headers=auth_a).json()
    positions = {habit["name"]: habit["sort_order"] for habit in listed}
    assert listed[0]["name"] == "Shower"
    assert positions["Shower"] == 1
    assert positions["Morning water"] == 4


def test_reordering_rejects_an_unknown_habit(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.patch(
        "/habits/reorder", headers=auth_a, json=[{"habit_id": 999999, "sort_order": 1}]
    )

    assert response.status_code == 404


def test_an_empty_board_can_be_built_up(
    client: TestClient, auth_b: dict[str, str]
) -> None:
    """This surface exists so User B can build a board from nothing."""
    assert client.get("/habits", headers=auth_b).json() == []

    created_bucket = client.post(
        "/buckets", headers=auth_b, json={"name": "Mornings", "color_hex": "#99B4D2"}
    )
    assert created_bucket.status_code == 201

    created_habit = client.post(
        "/habits",
        headers=auth_b,
        json={
            "bucket_id": created_bucket.json()["id"],
            "name": "Make the bed",
            "target_per_week": 7,
            "weekdays": [0, 1, 2, 3, 4, 5, 6],
            "sort_order": 1,
        },
    )
    assert created_habit.status_code == 201

    today = client.get("/today", headers=auth_b).json()
    assert [habit["name"] for habit in today["active"]] == ["Make the bed"]
    assert today["daily_pct"] == 0.0
