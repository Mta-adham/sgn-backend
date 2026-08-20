from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://sgn:sgn@localhost:5432/sgn"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    cors_origins: list[str] = ["http://localhost:3000"]
    stripe_secret_key: str = ""


settings = Settings()
