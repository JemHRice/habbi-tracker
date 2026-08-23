"""Device binding, login, throttling, session lifetime and logout."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import clock
from app.config import get_settings
from app.models import User
from tests.api.conftest import auth_header, login
from tests.conftest import PIN_A, TUESDAY, local_moment

WRONG_PIN = "000000"


def test_users_lists_names_only_and_needs_no_token(
    client: TestClient, user_a: User, user_b: User
) -> None:
    response = client.get("/users")

    assert response.status_code == 200
    body = response.json()
    assert [entry["display_name"] for entry in body] == ["User A", "User B"]
    assert set(body[0]) == {"id", "display_name"}


def test_login_issues_a_token_expiring_at_next_local_midnight(
    client: TestClient, user_a: User
) -> None:
    response = client.post("/auth/login", json={"user_id": user_a.id, "pin": PIN_A})

    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    # Frozen at 09:00 Monday in Sydney (UTC+11): next local midnight is 13:00 UTC.
    assert datetime.fromisoformat(body["expires_at"]) == datetime(
        2026, 3, 16, 13, 0, tzinfo=UTC
    )


def test_a_seeded_account_is_told_to_change_its_pin(
    client: TestClient, user_a: User
) -> None:
    response = client.post("/auth/login", json={"user_id": user_a.id, "pin": PIN_A})

    assert response.json()["must_change_pin"] is True


def test_a_wrong_pin_is_rejected(client: TestClient, user_a: User) -> None:
    response = client.post("/auth/login", json={"user_id": user_a.id, "pin": WRONG_PIN})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "PIN_INVALID"


def test_an_unknown_user_is_not_found(client: TestClient) -> None:
    response = client.post("/auth/login", json={"user_id": 9999, "pin": PIN_A})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_repeated_failures_trigger_a_cooldown(
    client: TestClient, user_a: User
) -> None:
    limit = get_settings().pin_throttle_max_attempts

    for _ in range(limit):
        rejected = client.post(
            "/auth/login", json={"user_id": user_a.id, "pin": WRONG_PIN}
        )
        assert rejected.status_code == 401

    throttled = client.post("/auth/login", json={"user_id": user_a.id, "pin": WRONG_PIN})

    assert throttled.status_code == 429
    assert throttled.json()["error"]["code"] == "PIN_THROTTLED"


def test_a_cooldown_blocks_even_the_correct_pin(
    client: TestClient, user_a: User
) -> None:
    """The check runs before verification, so guessing cannot be confirmed."""
    for _ in range(get_settings().pin_throttle_max_attempts):
        client.post("/auth/login", json={"user_id": user_a.id, "pin": WRONG_PIN})

    response = client.post("/auth/login", json={"user_id": user_a.id, "pin": PIN_A})

    assert response.status_code == 429


def test_a_cooldown_expires(client: TestClient, user_a: User, now: datetime) -> None:
    settings = get_settings()
    for _ in range(settings.pin_throttle_max_attempts):
        client.post("/auth/login", json={"user_id": user_a.id, "pin": WRONG_PIN})

    later = now + timedelta(seconds=settings.pin_throttle_cooldown_seconds + 1)
    with clock.frozen_time(later):
        response = client.post("/auth/login", json={"user_id": user_a.id, "pin": PIN_A})

    assert response.status_code == 200


def test_a_successful_login_clears_the_failure_count(
    client: TestClient, user_a: User
) -> None:
    settings = get_settings()
    for _ in range(settings.pin_throttle_max_attempts - 1):
        client.post("/auth/login", json={"user_id": user_a.id, "pin": WRONG_PIN})

    assert (
        client.post("/auth/login", json={"user_id": user_a.id, "pin": PIN_A}).status_code
        == 200
    )

    # The slate is clean, so a fresh run of failures is needed to trip it again.
    for _ in range(settings.pin_throttle_max_attempts - 1):
        assert (
            client.post(
                "/auth/login", json={"user_id": user_a.id, "pin": WRONG_PIN}
            ).status_code
            == 401
        )


def test_protected_routes_require_a_token(client: TestClient, user_a: User) -> None:
    response = client.get("/today")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_a_nonsense_token_is_rejected(client: TestClient, user_a: User) -> None:
    response = client.get("/today", headers=auth_header("not-a-real-token"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_a_token_stops_working_after_the_day_boundary(
    client: TestClient, user_a: User
) -> None:
    header = auth_header(login(client, user_a, PIN_A))
    assert client.get("/today", headers=header).status_code == 200

    with clock.frozen_time(local_moment(TUESDAY, hour=0, minute=1)):
        expired = client.get("/today", headers=header)

    assert expired.status_code == 401
    assert expired.json()["error"]["code"] == "UNAUTHENTICATED"


def test_logout_revokes_the_session(client: TestClient, user_a: User) -> None:
    header = auth_header(login(client, user_a, PIN_A))

    assert client.post("/auth/logout", headers=header).status_code == 204
    assert client.get("/today", headers=header).status_code == 401


def test_health_needs_no_token(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
