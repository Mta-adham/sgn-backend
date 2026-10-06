"""Production hardening that is observable from outside the app.

Two things are checked here, both of which only bite once the site is public:

- the interactive docs must not be served in production, since they publish the whole
  API surface;
- validation errors must come back as a readable string, because sbn-website renders
  `detail` straight into the UI and a list of error objects shows as "[object Object]".
"""

import importlib

import pytest
from fastapi.testclient import TestClient

import app.core.config as config_module
import app.main as main_module


def _client(environment: str) -> TestClient:
    """Rebuild the app under a given ENVIRONMENT.

    docs_url and friends are decided when FastAPI() is constructed, so the module has to
    be reimported rather than patched after the fact.
    """
    config_module.settings.environment = environment
    importlib.reload(main_module)
    return TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _restore_development_app():
    """Leave the module back in its development state for every other test."""
    yield
    config_module.settings.environment = "development"
    importlib.reload(main_module)


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_are_served_in_development(path: str) -> None:
    assert _client("development").get(path).status_code == 200


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_are_not_served_in_production(path: str) -> None:
    assert _client("production").get(path).status_code == 404


def test_health_still_works_in_production() -> None:
    response = _client("production").get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_validation_error_detail_is_a_string() -> None:
    """A list here renders as "[object Object]" in the frontend's error toast."""
    response = _client("development").post("/api/rsvp", json={"event_id": 1})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, str), f"expected a string, got {type(detail).__name__}"
    assert detail, "detail must not be empty"


def test_validation_error_names_the_offending_field() -> None:
    response = _client("development").post(
        "/api/contact", json={"email": "not-an-email", "message": "hello"}
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "email" in detail.lower()
    # The "body" prefix FastAPI includes is noise to a person reading a form error.
    assert not detail.startswith("body")


def test_malformed_rsvp_email_is_rejected() -> None:
    """RSVP email is the only link to a member account, so it has to be real."""
    response = _client("development").post(
        "/api/rsvp", json={"event_id": 1, "email": "typo-no-at-sign", "names": "Test"}
    )

    assert response.status_code == 422
    assert "email" in response.json()["detail"].lower()
