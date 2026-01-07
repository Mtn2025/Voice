import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine environment (default: development)
APP_ENV = os.getenv("APP_ENV", "development")

class Settings(BaseSettings):
    PROJECT_NAME: str = "Native Voice Orchestrator"
    API_V1_STR: str = "/api/v1"

    # Expose current env for debugging
    ACTIVE_ENV: str = APP_ENV

    # Telephony
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""

    # Telnyx
    TELNYX_API_KEY: str = ""
    TELNYX_API_BASE: str = "https://api.telnyx.com/v2"
    TELNYX_PUBLIC_KEY: str = ""  # For webhook signature validation (Punto A4)

    # AI Services
    AZURE_SPEECH_KEY: str = ""  # Hacer opcional para testing
    AZURE_SPEECH_REGION: str = ""  # Hacer opcional para testing
    GROQ_API_KEY: str = ""  # Hacer opcional para testing
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # =============================================================================
    # Database - Punto A6: NO DEFAULT PASSWORDS
    # =============================================================================
    # These MUST be set via environment variables (.env file or system env)
    # NEVER use default passwords in production
    # =============================================================================
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str = "db"  # Can default to "db" for Docker
    POSTGRES_PORT: str = "5432"  # Standard port
    POSTGRES_DB: str = "voice_db"

    # API Key for dashboard access (ETAPA 1 - desarrollo)
    # En producción será reemplazado por sistema JWT (ETAPA 2)
    ADMIN_API_KEY: str = ""

    # Security - Punto A4 (Webhook Validation)
    DEBUG: bool = False  # In DEBUG mode, webhook validation can be bypassed

    # =============================================================================
    # Redis - Punto A9 (State Management for Horizontal Scaling)
    # =============================================================================
    # Redis URL for sharing call state across multiple app instances
    # Format: redis://[host]:[port]/[db]
    # =============================================================================
    REDIS_URL: str = "redis://redis:6379/0"  # Default for Docker Compose

    @field_validator('POSTGRES_USER', 'POSTGRES_PASSWORD')
    @classmethod
    def validate_db_credentials(cls, v: str, info) -> str:
        """
        Validate database credentials are not using insecure defaults.

        Punto A6: Remove hardcoded passwords.
        """
        field_name = info.field_name

        # Reject empty credentials
        if not v or v.strip() == "":
            raise ValueError(
                f"{field_name} must be set in environment variables. "
                "Never use default passwords. Set in .env file or system environment."
            )

        # Reject common insecure values
        insecure_values = ['postgres', 'password', '123456', 'admin', 'root']
        if v.lower() in insecure_values:
            raise ValueError(
                f"{field_name} is using an insecure default value ('{v}'). "
                "Use a strong, unique password. Generate one with: "
                "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # Minimum length for passwords
        if field_name == 'POSTGRES_PASSWORD' and len(v) < 12:
            raise ValueError(
                f"POSTGRES_PASSWORD must be at least 12 characters long. "
                f"Current length: {len(v)}. Use a strong password."
            )

        return v

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Pydantic V2 Configuration
    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{APP_ENV}"),
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
        env_file_encoding="utf-8"
    )

settings = Settings()
