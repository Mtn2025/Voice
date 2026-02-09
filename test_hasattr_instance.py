"""Direct test to verify hasattr on instance"""
import asyncio
from app.db.database import get_db
from app.db.models import AgentConfig

async def test_hasattr():
    async for db in get_db():
        # Get first config using SQLAlchemy select
        from sqlalchemy import select
        stmt = select(AgentConfig).where(AgentConfig.id == 1)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if config:
            print(f"Config ID: {config.id}")
            print(f"Type: {type(config)}")
            print(f"\nTesting hasattr on INSTANCE:")
            print(f"  hasattr(config, 'stt_silence_timeout_telnyx'): {hasattr(config, 'stt_silence_timeout_telnyx')}")
            print(f"  hasattr(config, 'vad_threshold_telnyx'): {hasattr(config, 'vad_threshold_telnyx')}")
            
            print(f"\nTesting getattr on INSTANCE:")
            try:
                val = getattr(config, 'stt_silence_timeout_telnyx', 'NOT_FOUND')
                print(f"  getattr(config, 'stt_silence_timeout_telnyx'): {val}")
            except Exception as e:
                print(f"  ERROR: {e}")
            
            print(f"\nTesting hasattr on CLASS:")
            print(f"  hasattr(AgentConfig, 'stt_silence_timeout_telnyx'): {hasattr(AgentConfig, 'stt_silence_timeout_telnyx')}")
            
            print(f"\nDirect access:")
            try:
                print(f"  config.stt_silence_timeout_telnyx = {config.stt_silence_timeout_telnyx}")
            except AttributeError as e:
                print(f"  ERROR: {e}")
        else:
            print("No config found")
        break

if __name__ == "__main__":
    asyncio.run(test_hasattr())
