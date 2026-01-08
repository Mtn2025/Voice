# Run tests with environment variables
# Usage (PowerShell): .\run_tests.ps1
# Usage (Bash): bash run_tests.sh

# Set test environment variables
$env:POSTGRES_USER = "test_user"
$env:POSTGRES_PASSWORD = "test_password_safe"
$env:POSTGRES_SERVER = "localhost"
$env:POSTGRES_PORT = "5432"
$env:POSTGRES_DB = "test_voice_db"
$env:DEBUG = "True"

# Optional service keys (tests should mock these)
$env:AZURE_SPEECH_KEY = "test_azure_key"
$env:AZURE_SPEECH_REGION = "eastus"
$env:GROQ_API_KEY = "test_groq_key"
$env:TWILIO_ACCOUNT_SID = "test_twilio"
$env:TWILIO_AUTH_TOKEN = "test_token"
$env:TELNYX_API_KEY = "test_telnyx"
$env:ADMIN_API_KEY = "test_admin"
$env:REDIS_URL = "redis://localhost:6379/1"

# Run pytest
pytest $args
