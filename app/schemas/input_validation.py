"""
Pydantic Schemas for Input Validation - Punto A5

These schemas validate all user inputs to prevent injection attacks.
FastAPI automatically validates request data against these schemas.
"""


from pydantic import BaseModel, EmailStr, Field, field_validator


class AgentConfigUpdate(BaseModel):
    """
    Schema for updating agent configuration.

    Validates all dashboard form inputs to prevent XSS and injection attacks.
    """
    # Providers
    stt_provider: str | None = Field(None, max_length=50, pattern=r'^[a-z_]+$')
    stt_language: str | None = Field(None, max_length=10, pattern=r'^[a-z]{2}-[A-Z]{2}$')
    llm_provider: str | None = Field(None, max_length=50, pattern=r'^[a-z_]+$')
    llm_model: str | None = Field(None, max_length=100)
    extraction_model: str | None = Field(None, max_length=100)
    tts_provider: str | None = Field(None, max_length=50, pattern=r'^[a-z_]+$')

    # Voice configuration
    voice_name: str | None = Field(None, max_length=100)
    voice_style: str | None = Field(None, max_length=50)
    voice_speed: str | None = Field(None, pattern=r'^\d+(\.\d+)?$')  # Decimal number

    # Prompts and messages (sanitized separately)
    system_prompt: str | None = Field(None, max_length=10000)
    first_message: str | None = Field(None, max_length=500)

    # Numeric parameters
    interruption_threshold: int | None = Field(None, ge=0, le=20)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=4096)

    # Timeouts (milliseconds)
    initial_silence_timeout_ms: int | None = Field(None, ge=1000, le=60000)
    max_duration: int | None = Field(None, ge=60, le=3600)

    # Boolean flags
    enable_denoising: bool | None = None
    enable_end_call: bool | None = None

    @field_validator('system_prompt', 'first_message')
    @classmethod
    def sanitize_text_fields(cls, v: str | None) -> str | None:
        """Sanitize text fields to remove potentially dangerous content."""
        if not v:
            return v

        # Remove null bytes
        v = v.replace('\x00', '')

        # Remove script tags and other dangerous HTML
        dangerous_patterns = [
            '<script', '</script>',
            'javascript:',
            'onerror=', 'onload=',
            '<iframe', '</iframe>',
        ]

        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in v_lower:
                raise ValueError(f"Input contains dangerous pattern: {pattern}")

        return v.strip()

    @field_validator('llm_model', 'extraction_model')
    @classmethod
    def validate_model_name(cls, v: str | None) -> str | None:
        """Validate model names contain only safe characters."""
        if not v:
            return v

        # Allow alphanumeric, dash, dot, underscore
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError("Model name contains invalid characters")

        return v


class CallLogFilter(BaseModel):
    """
    Schema for filtering call logs.

    Prevents SQL injection in search queries.
    """
    search: str | None = Field(None, max_length=100)
    status: str | None = Field(None, pattern=r'^(completed|failed|in_progress)$')
    limit: int | None = Field(10, ge=1, le=100)
    offset: int | None = Field(0, ge=0)

    @field_validator('search')
    @classmethod
    def sanitize_search(cls, v: str | None) -> str | None:
        """Sanitize search query to prevent SQL injection."""
        if not v:
            return v

        # Remove SQL keywords and special characters
        dangerous_keywords = [
            'select', 'insert', 'update', 'delete', 'drop',
            'union', 'exec', '--', ';', '/*', '*/',
        ]

        v_lower = v.lower()
        for keyword in dangerous_keywords:
            if keyword in v_lower:
                raise ValueError(f"Search contains dangerous keyword: {keyword}")

        # Keep only alphanumeric, spaces, and basic punctuation
        import re
        v = re.sub(r'[^a-zA-Z0-9\s.@_-]', '', v)

        return v.strip()


class PhoneNumberInput(BaseModel):
    """
    Schema for phone number input.

    Validates phone number format.
    """
    phone_number: str = Field(..., min_length=10, max_length=20)

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number contains only safe characters."""
        import re

        # Remove all non-numeric characters except + - ( ) and spaces
        v = re.sub(r'[^0-9+\-() ]', '', v)

        # Must contain at least 10 digits
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10:
            raise ValueError("Phone number must contain at least 10 digits")

        return v.strip()


class EmailInput(BaseModel):
    """
    Schema for email input with built-in validation.
    """
    email: EmailStr  # Pydantic's EmailStr validates format automatically

    @field_validator('email')
    @classmethod
    def sanitize_email(cls, v: EmailStr) -> str:
        """Additional sanitization for email."""
        # Convert to lowercase
        email_str = str(v).lower().strip()

        # Reject emails with dangerous patterns
        if '<' in email_str or '>' in email_str:
            raise ValueError("Email contains invalid characters")

        return email_str


class APIKeyRotation(BaseModel):
    """
    Schema for API key rotation.

    Validates new API keys.
    """
    new_api_key: str = Field(..., min_length=32, max_length=128)
    confirm_api_key: str = Field(..., min_length=32, max_length=128)

    @field_validator('new_api_key', 'confirm_api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format."""
        import re

        # API keys should be alphanumeric + some special chars
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', v):
            raise ValueError("API key contains invalid characters")

        return v

    def __init__(self, **data):
        super().__init__(**data)
        # Validate keys match
        if self.new_api_key != self.confirm_api_key:
            raise ValueError("API keys do not match")
