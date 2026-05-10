from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "WardrobeWhiz API"
    debug: bool = True
    database_url: str = "sqlite:///./wardrobewhiz.db"
    upload_dir: str = "app/storage/uploads"
    thumbnail_dir: str = "app/storage/thumbnails"
    faiss_dir: str = "app/storage/faiss"
    jwt_secret_key: str = "wardrobewhiz-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    groq_api_key: str | None = None
    gemini_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
