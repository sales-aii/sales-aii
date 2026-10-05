# -*- coding: utf-8 -*-
"""
Configuration system for Sales.aii
"""

import sys
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_frozen() -> bool:
    """True when running inside a PyInstaller bundle"""
    return getattr(sys, "frozen", False)


def _resolve_base_dir() -> Path:
    """
    Resolve the writable application directory.

    When frozen, __file__ points inside PyInstaller's temporary extraction
    folder (_MEIPASS) which is deleted when the app exits. Using it would
    throw away the database and logs on every run, so the directory of the
    executable is used instead.
    """
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _resolve_env_file() -> Optional[str]:
    """Locate .env next to the executable (frozen) or in the project root"""
    base = _resolve_base_dir()
    for candidate in (base / ".env", Path.cwd() / ".env"):
        if candidate.is_file():
            return str(candidate)
    return None


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App info
    APP_NAME: str = "Sales.aii"
    APP_VERSION: str = "1.0.0"

    # Paths (resolved at runtime, not from env)
    BASE_DIR: Path = Field(default_factory=_resolve_base_dir, exclude=True)
    DATA_DIR: Path = Field(default_factory=lambda: _resolve_base_dir() / "data", exclude=True)
    LOGS_DIR: Path = Field(default_factory=lambda: _resolve_base_dir() / "logs", exclude=True)

    # Database
    DB_NAME: str = "sales_aii.db"
    DB_PATH: Optional[Path] = Field(default=None, exclude=True)

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "sales_aii.log"

    # Outbound HTTP
    HTTP_TIMEOUT: int = Field(default=30, description="Outbound API timeout in seconds")

    # AI provider selection
    AI_PROVIDER: str = Field(default="gemini", description="Active AI provider: gemini | mock")
    AI_TIMEOUT: int = Field(default=60, description="AI request timeout in seconds")
    AI_MAX_RETRIES: int = Field(default=3, description="AI retry attempts")

    # AI provider keys
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    GEMINI_MODEL: str = Field(default="gemini-3.8-flash", description="Gemini model id")

    # Platform integrations
    REDDIT_CLIENT_ID: Optional[str] = Field(default=None)
    REDDIT_CLIENT_SECRET: Optional[str] = Field(default=None)
    REDDIT_USER_AGENT: str = "Sales.aii/1.0.0"

    GITHUB_TOKEN: Optional[str] = Field(default=None)
    GITHUB_API_VERSION: str = "2022-11-28"

    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None)
    TELEGRAM_CHAT_ID: Optional[str] = Field(default=None)

    # Shopier uses a single Bearer token (Personal Access Token or OAuth 2.0
    # access token) - see https://developer.shopier.com/docs/creating-and-using-pats
    SHOPIER_API_TOKEN: Optional[str] = Field(default=None)
    # Legacy aliases kept so older .env files keep working
    SHOPIER_API_KEY: Optional[str] = Field(default=None)
    SHOPIER_API_SECRET: Optional[str] = Field(default=None)

    def model_post_init(self, __context) -> None:
        """Post init setup"""
        if self.DB_PATH is None:
            self.DB_PATH = self.DATA_DIR / self.DB_NAME
        # Ensure directories exist (parents needed when running from another dir)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()