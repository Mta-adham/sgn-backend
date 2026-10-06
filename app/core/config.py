from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The placeholder shipped in .env.example. Fine for local work, fatal in production:
# anyone who has read the repo could forge an admin token with it.
INSECURE_JWT_SECRET = "change-me"
MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://sgn:sgn@localhost:5434/sgn"
    jwt_secret: str = INSECURE_JWT_SECRET
    jwt_algorithm: str = "HS256"
    cors_origins: list[str] = ["http://localhost:3000"]
    stripe_secret_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    @model_validator(mode="after")
    def _reject_insecure_production_config(self) -> "Settings":
        """Refuse to boot a production deployment with development defaults.

        These are all failures that are silent at runtime and serious in effect, so the
        only safe moment to catch them is startup. A server that will not start is a
        problem you notice; one signing tokens with a published secret is not.
        """
        if not self.is_production:
            return self

        problems: list[str] = []

        if self.jwt_secret == INSECURE_JWT_SECRET:
            problems.append(
                "JWT_SECRET is still the example placeholder. Generate one with: "
                "python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        elif len(self.jwt_secret) < MIN_JWT_SECRET_LENGTH:
            problems.append(
                f"JWT_SECRET is only {len(self.jwt_secret)} characters; "
                f"use at least {MIN_JWT_SECRET_LENGTH}."
            )

        if "*" in self.cors_origins:
            # allow_credentials=True plus a wildcard origin means any site can make
            # authenticated requests on a logged-in member's behalf.
            problems.append("CORS_ORIGINS cannot be '*' when credentials are allowed.")

        insecure_origins = [
            origin
            for origin in self.cors_origins
            if origin.startswith("http://") and "localhost" not in origin
            and "127.0.0.1" not in origin
        ]
        if insecure_origins:
            problems.append(f"CORS_ORIGINS must use https in production: {insecure_origins}")

        if not self.cors_origins:
            problems.append("CORS_ORIGINS is empty; the frontend would be blocked.")

        if problems:
            raise ValueError(
                "Refusing to start with an insecure production configuration:\n  - "
                + "\n  - ".join(problems)
            )

        return self


settings = Settings()
