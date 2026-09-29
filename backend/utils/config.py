from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from pydantic import field_validator
from typing import Annotated, List


class Settings(BaseSettings):
    database_url: str = "postgresql://user:password@localhost/db"
    hindsight_base_url: str = "http://hindsight:8888"
    hindsight_bank_id: str = "supply-chain-memory"
    google_api_key: str = ""
    # Optional API key guarding state-changing endpoints (see utils.security).
    api_key: str = ""
    # NoDecode: pass the raw env string through (pydantic-settings would try to
    # JSON-parse list fields and raise SettingsError on "a,b,c").
    allowed_origins: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:80",
    ]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Accept comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
