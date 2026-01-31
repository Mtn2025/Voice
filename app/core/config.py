import logging
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine environment (default: development)
APP_ENV = os.getenv("APP_ENV", "development")

class Settings(BaseSettings):
    """
    Centralized Application Configuration.

    Manages environment variables, security credentials, and system settings.
    Prioritizes environment variables for all sensitive data (Coolify/Prod compliant).
    """
    PROJECT_NAME: str = "Native Voice Orchestrator"
    API_V1_STR: str = "/api/v1"

    # Debugging context
    ACTIVE_ENV: str = APP_ENV

    # --- Telephony Providers ---
    # Should be provided via env vars in production
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""

    TELNYX_API_KEY: str = ""
    TELNYX_API_BASE: str = "https://api.telnyx.com/v2"
    TELNYX_PUBLIC_KEY: str = ""  # Used for webhook signature validation

    # --- AI Services ---
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = "eastus"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Provider Selection (Environment-based)
    DEFAULT_STT_PROVIDER: str = "azure"
    DEFAULT_LLM_PROVIDER: str = "groq"
    DEFAULT_TTS_PROVIDER: str = "azure"

    # --- VAD Stability ---
    VAD_CONFIRMATION_WINDOW_MS: int = 200
    VAD_ENABLE_CONFIRMATION: bool = True

    # --- Azure OpenAI ---
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4o"
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"

    # --- Database Credentials ---
    # STRICT: Must be set via environment variables (no defaults in code).
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "voice_db"

    # --- Security ---
    ADMIN_API_KEY: str = ""
    DEBUG: bool = False

    # --- Infrastructure (Redis) ---
    REDIS_URL: str = "redis://redis:6379/0"

    # --- Consolidated Validators ---

    @field_validator('POSTGRES_USER', 'POSTGRES_PASSWORD')
    @classmethod
    def validate_db_credentials(cls, v: str, info) -> str:
        """
        Validate database credentials.
        Enforces that values must come from environment (not empty).
        Only checks password complexity, respects configured username (Coolify compliant).
        """
        field_name = info.field_name

        # Reject empty
        if not v or not v.strip():
            raise ValueError(f"{field_name} must be set via environment variables.")

        # Password complexity check (but not username blocking)
        if field_name == 'POSTGRES_PASSWORD':
            # Check for weak passwords if in production context
            weak_passwords = ['password', '123456', 'admin', 'root']
            if v.lower() in weak_passwords:
                raise ValueError(f"POSTGRES_PASSWORD uses an insecure value ('{v}'). Change it in your environment variables.")

            if len(v) < 8:
                 # Warn but dont always crash to allow local dev simple passwords if desired,
                 # or enforce strictly. Given "Strict Audit", we enforce min length.
                 raise ValueError("POSTGRES_PASSWORD must be at least 8 characters long.")

        return v

    @field_validator('AZURE_SPEECH_KEY', 'GROQ_API_KEY')
    @classmethod
    def validate_ai_keys(cls, v: str, info) -> str:
        """Log warnings for missing AI keys (Non-blocking startup)."""
        if not v or not v.strip():
            logging.getLogger(__name__).warning(
                f"⚠️ [Config] {info.field_name} is not set. AI services may fail."
            )
        return v

    @field_validator('ADMIN_API_KEY')
    @classmethod
    def validate_admin_key(cls, v: str) -> str:
        """Validate ADMIN_API_KEY is present."""
        if not v or not v.strip():
             # Exception for test env
             if os.getenv("APP_ENV") == "test":
                 return "test_key"
             raise ValueError("ADMIN_API_KEY must be set via environment variables.")
        return v

    @property
    def DATABASE_URL(self) -> str:
        """
        Constructs the Database URL.
        Prioritizes explicit `DATABASE_URL` env var.
        """
        if os.getenv("DATABASE_URL"):
            url = os.getenv("DATABASE_URL")
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://")
            return url

        from urllib.parse import quote_plus
        return f"postgresql+asyncpg://{quote_plus(self.POSTGRES_USER)}:{quote_plus(self.POSTGRES_PASSWORD)}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Pydantic V2 Configuration
    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{APP_ENV}"),
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
        env_file_encoding="utf-8"
    )

# =============================================================================
# Global Settings Instance
# =============================================================================
_settings: Settings | None = None

def get_settings() -> Settings:
    """Get or create the global Settings instance (Singleton)."""
    global _settings  # noqa: PLW0603 - Singleton pattern for app config
    if _settings is None:
        _settings = Settings()
    return _settings

settings = get_settings()
