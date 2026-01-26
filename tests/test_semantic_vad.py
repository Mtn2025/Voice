
import asyncio
import logging
import time
import sys
import os

# Ensure app module is found
sys.path.append(os.getcwd())

from typing import AsyncGenerator

from app.core.frames import TextFrame, Frame
from app.processors.logic.aggregator import ContextAggregator
from app.services.base import LLMProvider

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockLLMProvider(LLMProvider):
    def __init__(self, responses: dict):
        self.responses = responses
        
    async def get_stream(self, messages: list, system_prompt: str, temperature: float, max_tokens: int = 600, model=None) -> AsyncGenerator[str, None]:
        # Extract text from last message
        text = messages[-1]['content'].replace('Text: "', '').replace('"', '')
        
        # Determine response
        # Simple heuristic for test: if text ends with "...", it's incomplete
        resp = "NO" if text.endswith("...") else "YES"
        
        logger.info(f"🤖 [MOCK LLM] Check '{text}' -> {resp}")
        yield resp

class MockDownstream:
    def __init__(self):
        self.received_frames = []
        
    async def process_frame(self, frame, direction):
        self.received_frames.append((time.time(), frame))

async def test_semantic_turn_detection():
    # Setup
    mock_llm = MockLLMProvider({})
    history = []
    config = type('Config', (), {})() # Empty object
    
    aggregator = ContextAggregator(config, history, llm_provider=mock_llm)
    downstream = MockDownstream()
    
    # Manually link downstream (Pipeline usually does this)
    # Aggregator inherits FrameProcessor -> has _next_msg_processor logic?
    # We need to monkeypatch or use add_downstream if available, 
    # but FrameProcessor usually takes a 'next_processor' or we can just override 'push_frame'
    
    async def capture_push(frame, direction=1):
        await downstream.process_frame(frame, direction)
        
    aggregator.push_frame = capture_push
    
    print("\n--- Test 1: Complete Sentence ---")
    start_t = time.time()
    await aggregator.process_frame(TextFrame(text="Hola mundo"), 1) # 1 = Downstream
    
    # Wait enough for initial timeout (0.6s) + processing
    await asyncio.sleep(0.8) 
    
    # Should have received frame
    assert len(downstream.received_frames) == 1
    t1, f1 = downstream.received_frames[0]
    delay = t1 - start_t
    print(f"Delay 1: {delay:.2f}s (Expect ~0.6s)")
    assert 0.6 <= delay < 1.0 # Semantic check should be fast/skipped if YES
    assert f1.text == "Hola mundo"
    
    print("\n--- Test 2: Incomplete Sentence ---")
    downstream.received_frames = []
    start_t = time.time()
    await aggregator.process_frame(TextFrame(text="Quiero comprar un..."), 1)
    
    # Wait initial timeout (0.6s) -> Should NOT have frame yet if Logic works
    await asyncio.sleep(0.7)
    if len(downstream.received_frames) > 0:
        print("❌ Failed: Initial timeout didn't wait for semantic check or check returned YES early.")
    else:
        print("✅ Correctly waiting...")
        
    # Wait full semantic timeout (1.2s total)
    await asyncio.sleep(0.6)
    
    assert len(downstream.received_frames) == 1
    t2, f2 = downstream.received_frames[0]
    delay = t2 - start_t
    print(f"Delay 2: {delay:.2f}s (Expect ~1.2s)")
    
    # Allow some buffer
    assert delay >= 1.2
    assert f2.text == "Quiero comprar un..."

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_semantic_turn_detection())
    print("\n✅ Tests Completed")
