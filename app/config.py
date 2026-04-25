from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./clinical_intake.db"
    upload_dir: str = "./uploads"
    min_text_chars: int = 50
    low_confidence_threshold: float = 0.5


settings = Settings()
