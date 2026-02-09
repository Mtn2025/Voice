
$env:POSTGRES_SERVER="localhost"
$env:POSTGRES_PORT="5432"
$env:REDIS_URL="redis://localhost:6379/0"
# Ensure we use the right Python executable
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
