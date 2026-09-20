from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+psycopg://quiz:quiz@localhost:5432/quiz"
    secret_key: str  # no defaults for secrets: the app refuses to start without them
    admin_username: str = "admin"
    admin_password: str
    token_minutes: int = 60


settings = Settings()
