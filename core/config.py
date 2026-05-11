"""
core/config.py — Application settings loaded from environment variables.
All Azure service bindings, model settings, and classification parameters live here.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "Narrative Harm Classifier"
    app_version: str = "1.0.0"
    debug: bool = False

    # --- Azure ---
    azure_text_analytics_endpoint: str = ""
    azure_text_analytics_key: str = ""
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "classifications"
    azure_function_app_name: str = ""

    # --- Database (Azure SQL or PostgreSQL) ---
    database_url: str = "sqlite:///./dev.db"  # override with Azure SQL in prod

    # --- Classification ---
    taxonomy_config_path: str = str(
        Path(__file__).parent.parent / "config" / "taxonomy_v1.yaml"
    )
    taxonomy_version: str = "1.0.0"
    default_confidence_threshold: float = 0.65
    context_window_tokens: int = 256
    max_text_length: int = 10000

    # --- Logging ---
    log_level: str = "INFO"
    log_format: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
