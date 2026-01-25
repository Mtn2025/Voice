import asyncio
import logging
import sys
import os
from types import SimpleNamespace

# Add project root
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Simulation")

from app.core.pipeline import Pipeline
from app.core.frames import AudioFrame, TextFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame
# Processors
from app.processors.logic.stt import STTProcessor
from app.processors.logic.aggregator import ContextAggregator
from app.processors.logic.llm import LLMProcessor
from app.processors.logic.tts import TTSProcessor

# Mocks
from tests.simulation.mock_providers import MockSTTProvider, MockLLMProvider, MockTTSProvider

async def run_simulation():
    logger.info("🚀 Starting Pipeline Simulation...")

    # 1. Mock Config
    config = SimpleNamespace(
        client_type='twilio', 
        stt_language='es-MX',
        system_prompt='You are a helpful assistant.'
    )

    # 2. Providers
    stt_provider = MockSTTProvider()
    llm_provider = MockLLMProvider()
    tts_provider = MockTTSProvider()

    # 3. Processors
    # Need loop for STT
    loop = asyncio.get_running_loop()
    
    stt = STTProcessor(provider=stt_provider, config=config, loop=loop)
    # Skip VAD for simulation simplicity (or mock it if needed)
    # vad = VADProcessor(config) 
    # Mock Aggregator history
    history = []
    agg = ContextAggregator(config=config, conversation_history=history)
    llm = LLMProcessor(provider=llm_provider, config=config, conversation_history=history)
    tts = TTSProcessor(provider=tts_provider, config=config)

    # 4. Build Pipeline
    # Manual linkage without VAD
    pipeline = Pipeline([stt, agg, llm, tts])
    
    # 5. Initialize
    logger.info("🔧 Initializing Processors...")
    await stt.initialize() # This creates the recognizer
    await tts.initialize()
    await pipeline.start()

    # 6. Simulate Input
    logger.info("🗣️ Simulating User Speech: 'Hola Andrea'")
    
    # Access the recognizer created inside STTProcessor
    # STTProcessor.recognizer is the instance returned by MockSTTProvider
    if stt.recognizer:
        stt.recognizer.simulate_speech("Hola Andrea")
    else:
        logger.error("❌ STT Recognizer not initialized!")
        return

    # 7. Wait for processing
    # The pipeline is async. We need to wait enough time for the flow:
    # STT Event -> TextFrame -> Aggregator (0.6s timeout) -> LLM -> TTS
    
    logger.info("⏳ Waiting for pipeline processing (Aggregator timeout 0.6s + LLM + TTS)...")
    await asyncio.sleep(2.0)
    
    # 8. Verify State
    logger.info("🔍 Verifying Logic...")
    
    # Check Aggregator History
    if len(history) >= 1 and history[-1]["role"] == "user":
        logger.info(f"✅ Aggregator recorded user turn: {history[-1]['content']}")
    else:
        logger.error(f"❌ Aggregator failed to record turn. History: {history}")

    # Check LLM History (should include assistant response)
    # LLMProcessor updates history? No, wait. 
    # LLMProcessor receives TextFrame (Full Turn).
    # Its logic: generates stream -> pushes AudioFrames?
    # Does it update history?
    # `app/processors/logic/llm.py` usually updates history with the assistant response.
    # Let's check history again.
    
    has_assistant = any(m["role"] == "assistant" for m in history)
    if has_assistant:
        logger.info("✅ LLM response found in history.")
    else:
        logger.warning(f"⚠️ LLM response NOT found in history. (Maybe incomplete simulation time?) History: {history}")

    # 9. Cleanup
    await pipeline.stop()
    await stt.cleanup()
    logger.info("🏁 Simulation Complete.")

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"❌ Simulation Failed: {e}")
        import traceback
        traceback.print_exc()
