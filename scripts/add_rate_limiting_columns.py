import asyncio

from sqlalchemy import text

from app.db.database import engine


async def add_rate_limiting_columns():
    """Add rate limiting configuration columns to agent_configs table."""

    queries = [
        "ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS rate_limit_global INTEGER DEFAULT 200",
        "ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS rate_limit_twilio INTEGER DEFAULT 30",
        "ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS rate_limit_telnyx INTEGER DEFAULT 50",
        "ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS rate_limit_websocket INTEGER DEFAULT 100",
        "ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS limit_groq_tokens_per_min INTEGER DEFAULT 100000",
        "ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS limit_azure_requests_per_min INTEGER DEFAULT 100",
        "ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS limit_twilio_calls_per_hour INTEGER DEFAULT 100",
        "ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS limit_telnyx_calls_per_hour INTEGER DEFAULT 100"
    ]

    async with engine.begin() as conn:
        for query in queries:
            await conn.execute(text(query))
            print(f"✅ Executed: {query[:60]}...")

    print("\n✅ All rate limiting columns added successfully!")

if __name__ == "__main__":
    asyncio.run(add_rate_limiting_columns())
