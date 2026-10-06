"""The production configuration guard in app/core/config.py.

Every case here is a misconfiguration that a running server would not complain about:
tokens signed with a published secret, or any origin allowed to make credentialed
requests. Startup is the only point at which they can still be caught.
"""

import pytest

from app.core.config import INSECURE_JWT_SECRET, Settings

GOOD_SECRET = "x" * 48


def _settings(**overrides: object) -> Settings:
    """Build Settings from explicit values only, ignoring any real .env on disk."""
    defaults: dict[str, object] = {
        "environment": "production",
        "database_url": "postgresql+asyncpg://u:p@db/sgn",
        "jwt_secret": GOOD_SECRET,
        "jwt_algorithm": "HS256",
        "cors_origins": ["https://saudiglobal.co"],
        "stripe_secret_key": "",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


def test_valid_production_config_is_accepted() -> None:
    settings = _settings()
    assert settings.is_production
    assert settings.cors_origins == ["https://saudiglobal.co"]


@pytest.mark.parametrize("environment", ["production", "Production", "PROD", " prod "])
def test_production_is_detected_case_and_space_insensitively(environment: str) -> None:
    assert _settings(environment=environment).is_production


@pytest.mark.parametrize("environment", ["development", "staging", "test", ""])
def test_non_production_environments_skip_the_guard(environment: str) -> None:
    # Development must stay frictionless: the placeholder secret is expected there.
    settings = _settings(
        environment=environment,
        jwt_secret=INSECURE_JWT_SECRET,
        cors_origins=["http://localhost:3000"],
    )
    assert not settings.is_production
    assert settings.jwt_secret == INSECURE_JWT_SECRET


def test_placeholder_secret_is_rejected_in_production() -> None:
    with pytest.raises(ValueError, match="example placeholder"):
        _settings(jwt_secret=INSECURE_JWT_SECRET)


def test_short_secret_is_rejected_in_production() -> None:
    with pytest.raises(ValueError, match="characters"):
        _settings(jwt_secret="tooshort")


def test_wildcard_cors_is_rejected_in_production() -> None:
    with pytest.raises(ValueError, match="cannot be"):
        _settings(cors_origins=["*"])


def test_plain_http_origin_is_rejected_in_production() -> None:
    with pytest.raises(ValueError, match="https"):
        _settings(cors_origins=["http://saudiglobal.co"])


def test_localhost_origin_is_allowed_in_production() -> None:
    # Deliberate: an operator tunnelling to a live instance is a normal thing to do, and
    # localhost is not an origin an attacker can serve from.
    settings = _settings(cors_origins=["https://saudiglobal.co", "http://localhost:3000"])
    assert "http://localhost:3000" in settings.cors_origins


def test_empty_cors_is_rejected_in_production() -> None:
    with pytest.raises(ValueError, match="empty"):
        _settings(cors_origins=[])


def test_all_problems_are_reported_together() -> None:
    """One restart should surface every problem, not just the first."""
    with pytest.raises(ValueError) as exc:
        _settings(jwt_secret=INSECURE_JWT_SECRET, cors_origins=["*"])

    message = str(exc.value)
    assert "placeholder" in message
    assert "CORS_ORIGINS" in message
