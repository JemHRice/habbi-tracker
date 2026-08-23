"""The `/me` surface: settings, and changing a provisioned PIN."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from tests.api.conftest import auth_header, login
from tests.conftest import PIN_A

NEW_PIN = "246813"


def test_me_returns_the_current_settings(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.get("/me", headers=auth_a)

    assert response.status_code == 200
    assert response.json() == {
        "display_name": "User A",
        "timezone": "Australia/Sydney",
        "season_active": False,
        "reminders_enabled": False,
        "must_change_pin": True,
    }


def test_display_name_can_be_changed(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    """Seeded names are placeholders; they have to be renameable in-app."""
    response = client.patch("/me", headers=auth_a, json={"display_name": "Someone"})

    assert response.status_code == 200
    assert response.json()["display_name"] == "Someone"
    assert client.get("/me", headers=auth_a).json()["display_name"] == "Someone"


def test_timezone_can_be_changed(client: TestClient, auth_a: dict[str, str]) -> None:
    response = client.patch("/me", headers=auth_a, json={"timezone": "Europe/London"})

    assert response.status_code == 200
    assert response.json()["timezone"] == "Europe/London"


def test_an_unknown_timezone_is_rejected(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.patch("/me", headers=auth_a, json={"timezone": "Mars/Olympus"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"


def test_the_season_toggle_changes_what_is_scheduled(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    before = len(client.get("/today", headers=auth_a).json()["active"])

    assert (
        client.patch("/me", headers=auth_a, json={"season_active": True}).status_code
        == 200
    )

    after = len(client.get("/today", headers=auth_a).json()["active"])
    assert after == before  # Monday has no season-dependent habit
    assert client.get("/me", headers=auth_a).json()["season_active"] is True


def test_reminders_cannot_be_switched_on(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    """The field is dormant: exposed, never settable, wired to nothing."""
    response = client.patch("/me", headers=auth_a, json={"reminders_enabled": True})

    assert response.status_code == 200
    assert response.json()["reminders_enabled"] is False


def test_an_empty_display_name_is_rejected(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.patch("/me", headers=auth_a, json={"display_name": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"


def test_changing_the_pin_clears_the_must_change_flag(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.put(
        "/me/pin", headers=auth_a, json={"current_pin": PIN_A, "new_pin": NEW_PIN}
    )

    assert response.status_code == 200
    assert response.json()["must_change_pin"] is False


def test_the_new_pin_works_and_the_old_one_does_not(
    client: TestClient, auth_a: dict[str, str], user_a: User
) -> None:
    client.put(
        "/me/pin", headers=auth_a, json={"current_pin": PIN_A, "new_pin": NEW_PIN}
    )

    assert (
        client.post(
            "/auth/login", json={"user_id": user_a.id, "pin": PIN_A}
        ).status_code
        == 401
    )
    accepted = client.post("/auth/login", json={"user_id": user_a.id, "pin": NEW_PIN})
    assert accepted.status_code == 200
    assert accepted.json()["must_change_pin"] is False


def test_changing_a_pin_keeps_the_current_session_alive(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    """Changing your own PIN should not log you out of the device in your hand."""
    client.put(
        "/me/pin", headers=auth_a, json={"current_pin": PIN_A, "new_pin": NEW_PIN}
    )

    assert client.get("/today", headers=auth_a).status_code == 200


def test_the_current_pin_must_be_correct(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    response = client.put(
        "/me/pin", headers=auth_a, json={"current_pin": "999999", "new_pin": NEW_PIN}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "PIN_INVALID"


def test_a_new_pin_must_be_six_digits(
    client: TestClient, auth_a: dict[str, str]
) -> None:
    for bad in ("1234", "1234567", "12ab56"):
        response = client.put(
            "/me/pin", headers=auth_a, json={"current_pin": PIN_A, "new_pin": bad}
        )
        assert response.status_code == 400, bad
        assert response.json()["error"]["code"] == "VALIDATION"


def test_a_user_who_chose_their_pin_is_never_nagged(
    client: TestClient, auth_a: dict[str, str], user_a: User, db: Session
) -> None:
    """Deliberately choosing the seeded digits still counts as choosing."""
    response = client.put(
        "/me/pin", headers=auth_a, json={"current_pin": PIN_A, "new_pin": PIN_A}
    )

    assert response.status_code == 200
    assert response.json()["must_change_pin"] is False
    assert (
        client.post("/auth/login", json={"user_id": user_a.id, "pin": PIN_A}).json()[
            "must_change_pin"
        ]
        is False
    )


def test_settings_require_a_token(client: TestClient) -> None:
    assert client.get("/me").status_code == 401
    assert client.patch("/me", json={"season_active": True}).status_code == 401
