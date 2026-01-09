
import asyncio

from sqlalchemy import select, update

from app.db.database import AsyncSessionLocal
from app.db.models import AgentConfig


async def update_config():
    async with AsyncSessionLocal() as session:
        print("🔍 Checking for existing configuration...")
        result = await session.execute(select(AgentConfig))
        config = result.scalars().first()

        if config:
            print(f"📝 Found config '{config.name}'. Updating to optimal parameters...")

            # Universal Update
            stmt = (
                update(AgentConfig)
                .where(AgentConfig.id == config.id)
                .values(
                    # Phone Profile
                    initial_silence_timeout_ms_phone=30000,
                    silence_timeout_ms_phone=2000,

                    # Telnyx Profile
                    initial_silence_timeout_ms_telnyx=30000,
                    silence_timeout_ms_telnyx=2000,

                    # General
                    initial_silence_timeout_ms=30000,

                    # Ensure stt_language is set (optional hygiene)
                    stt_language="es-MX"
                )
            )
            await session.execute(stmt)
            await session.commit()
            print("✅ Configuration updated successfully!")
            print("   - Initial Silence: 30s")
            print("   - Segmentation Silence: 2s")
        else:
            print("⚠️ No configuration found to update.")

if __name__ == "__main__":
    asyncio.run(update_config())
