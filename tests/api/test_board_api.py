"""The board reads, and the materialisation they trigger."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FactCompletion, User
from tests.conftest import REFERENCE_MONDAY, SEED_MOMENT


def test_today_returns_the_home_screen(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.get("/today", headers=auth_a)

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "today"
    assert body["date"] == REFERENCE_MONDAY.isoformat()
    assert body["editable"] is True
    assert body["done_count"] == 0
    assert body["remaining_count"] == len(body["active"]) > 0
    assert body["daily_pct"] == 0.0


def test_today_orders_active_habits_for_display(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    active = client.get("/today", headers=auth_a).json()["active"]

    keys = [(habit["anytime"], habit["sort_order"]) for habit in active]
    assert keys == sorted(keys)
    assert active[-1]["name"] == "Daily check-in"
    assert active[-2]["name"] == "Water through the day"


def test_today_offers_unscheduled_habits_as_extras(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    body = client.get("/today", headers=auth_a).json()

    scheduled = {habit["name"] for habit in body["active"]}
    extras = {habit["name"] for habit in body["available_extras"]}
    assert "Laundry" in extras
    assert extras.isdisjoint(scheduled)


def test_reading_the_board_materialises_the_missed_days(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    """The user was seeded a fortnight ago and has not opened the app since."""
    before = db.scalar(
        select(func.count()).select_from(FactCompletion).where(
            FactCompletion.user_id == user_a.id
        )
    )
    assert before == 0

    client.get("/today", headers=auth_a)

    days = set(
        db.scalars(
            select(FactCompletion.date).where(FactCompletion.user_id == user_a.id)
        ).all()
    )
    assert min(days) == SEED_MOMENT.date()
    assert max(days) == REFERENCE_MONDAY


def test_reading_never_materialises_before_the_user_existed(
    client: TestClient, auth_a: dict[str, str], db: Session, user_a: User
) -> None:
    """Backfill fills up to today; it never writes history that never happened."""
    client.get("/months/2026/1", headers=auth_a)

    earliest = db.scalar(
        select(func.min(FactCompletion.date)).where(FactCompletion.user_id == user_a.id)
    )
    assert earliest == SEED_MOMENT.date()


def test_day_detail_returns_the_documented_shape(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    client.get("/today", headers=auth_a)
    response = client.get(f"/days/{REFERENCE_MONDAY.isoformat()}", headers=auth_a)

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "day"
    assert body["date"] == REFERENCE_MONDAY.isoformat()
    assert body["editable"] is True
    assert body["no_data"] is False
    assert body["final_pct"] == 0.0
    assert body["not_completed"]


def test_a_locked_empty_day_reads_as_no_data(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    locked = REFERENCE_MONDAY - timedelta(days=5)

    client.get("/today", headers=auth_a)
    body = client.get(f"/days/{locked.isoformat()}", headers=auth_a).json()

    assert body["no_data"] is True
    assert body["editable"] is False


def test_a_malformed_date_is_a_validation_error(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.get("/days/not-a-date", headers=auth_a)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"


def test_weeks_defaults_to_the_current_week(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.get("/weeks", headers=auth_a)

    assert response.status_code == 200
    body = response.json()
    assert body["week_start"] == REFERENCE_MONDAY.isoformat()
    assert len(body["days"]) == 7
    assert [day["weekday"] for day in body["days"]] == list(range(7))


def test_weeks_accepts_any_date_in_the_week(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    saturday = REFERENCE_MONDAY + timedelta(days=5)

    body = client.get(
        "/weeks", headers=auth_a, params={"containing_date": saturday.isoformat()}
    ).json()

    assert body["week_start"] == REFERENCE_MONDAY.isoformat()
    assert body["week_end"] == (REFERENCE_MONDAY + timedelta(days=6)).isoformat()


def test_months_returns_rates_and_a_full_calendar(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    client.get("/today", headers=auth_a)
    response = client.get("/months/2026/3", headers=auth_a)

    assert response.status_code == 200
    body = response.json()
    assert body["year"] == 2026
    assert body["month"] == 3
    assert len(body["days"]) == 31
    assert body["habits"]
    assert all(0.0 <= row["rate"] <= 1.0 for row in body["habits"] if row["rate"] is not None)


def test_an_out_of_range_month_is_rejected(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.get("/months/2026/13", headers=auth_a)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"


def test_an_empty_board_reads_as_a_rest_day(
    client: TestClient, auth_b: dict[str, str]
) -> None:
    body = client.get("/today", headers=auth_b).json()

    assert body["daily_pct"] is None
    assert body["active"] == []
    assert body["available_extras"] == []
    assert body["done_count"] == 0
