"""
Simulation Script - Barge-In Testing (FIXED FSM TRANSITIONS).

Simulates complete conversation flow with interruption to validate:
- FSM state transitions (CORRECTED PATHS)
- Barge-in reactivity (< 100ms)
- Audio pipeline cleanup
- Latency measurements

Run: python run_simulation.py
"""
import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.mocks import MockTelephonyAdapter, MockUserAdapter, UserAction
from app.domain.state.conversation_state import ConversationFSM, ConversationState
from app.core.control_channel import ControlChannel, ControlSignal
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SimulationOrchestrator:
    """
    Simplified orchestrator for simulation.
    
    Mimics VoiceOrchestratorV2 behavior for testing.
    """
    
    def __init__(self):
        self.fsm = ConversationFSM()
        self.control_channel = ControlChannel()
        self.telephony = MockTelephonyAdapter(latency_ms=50)
        self.user = MockUserAdapter(self.telephony)
        
        self.is_speaking = False
        self.speaking_task = None
        
        # Event log for validation
        self.event_log = []
        self.start_time = None
    
    def log_event(self, event_type: str, details: str):
        """Log event with timestamp."""
        if not self.start_time:
            self.start_time = datetime.now()
        
        elapsed_ms = (datetime.now() - self.start_time).total_seconds() * 1000
        
        self.event_log.append({
            'timestamp': datetime.now(),
            'elapsed_ms': elapsed_ms,
            'event_type': event_type,
            'details': details,
            'fsm_state': self.fsm.state.value
        })
        
        logger.info(
            f"📊 t={elapsed_ms:6.0f}ms | "
            f"FSM: {self.fsm.state.value:12s} | "
            f"{event_type:15s} | {details}"
        )
    
    async def start(self):
        """Start simulation."""
        await self.telephony.connect()
        self.telephony.register_audio_callback(self.on_audio_received)
        
        # Start control loop
        self.control_task = asyncio.create_task(self._control_loop())
        
        self.log_event("SYSTEM_INIT", "Orchestrator started")
        # ✅ FIX: Valid transition idle -> listening
        await self.fsm.transition(ConversationState.LISTENING, "System ready")
    
    async def on_audio_received(self, audio_data: bytes):
        """Handle incoming audio (from mock user)."""
        data_str = audio_data.decode('utf-8')
        
        if data_str.startswith("INTERRUPT:"):
            text = data_str.replace("INTERRUPT:", "")
            self.log_event("INTERRUPT", f"User interrupted: '{text}'")
            
            # Send interrupt signal
            await self.control_channel.send(
                ControlSignal.INTERRUPT,
                metadata={'text': text}
            )
        
        elif data_str.startswith("AUDIO:"):
            text = data_str.replace("AUDIO:", "")
            self.log_event("AUDIO_RX", f"User spoke: '{text}'")
            
            # ✅ FIX: Valid transition listening -> processing
            await self.fsm.transition(ConversationState.PROCESSING, "User input received")
            
            # Simulate STT + LLM processing (300ms)
            await asyncio.sleep(0.3)
            
            # Start speaking
            await self.start_speaking(f"Response to: {text}")
    
    async def start_speaking(self, response: str):
        """Simulate TTS and speaking."""
        can_speak = await self.fsm.can_speak()
        if not can_speak:
            self.log_event("SPEAK_BLOCKED", f"Cannot speak in state {self.fsm.state.value}")
            return
        
        await self.fsm.transition(ConversationState.SPEAKING, "Starting TTS")
        self.log_event("TTS_START", f"Speaking: '{response}'")
        
        self.is_speaking = True
        
        # Simulate TTS streaming (2 seconds of audio)
        self.speaking_task = asyncio.create_task(self._simulate_tts(response))
    
    async def _simulate_tts(self, text: str):
        """Simulate TTS audio streaming."""
        try:
            # Simulate streaming audio in chunks
            chunks = 20  # 2 seconds / 100ms per chunk
            for i in range(chunks):
                if not self.is_speaking:
                    self.log_event("TTS_STOP", "TTS interrupted")
                    break
                
                # Send audio chunk
                audio_chunk = f"TTS_CHUNK_{i}".encode('utf-8')
                await self.telephony.send_audio(audio_chunk)
                
                await asyncio.sleep(0.1)  # 100ms per chunk
            
            if self.is_speaking:
                # Completed without interruption
                self.is_speaking = False
                self.log_event("TTS_COMPLETE", "Finished speaking")
                await self.fsm.transition(ConversationState.LISTENING, "Waiting for user")
        
        except asyncio.CancelledError:
            self.log_event("TTS_CANCELLED", "Task cancelled")
            raise
    
    async def _control_loop(self):
        """Control loop for handling interruptions."""
        while True:
            try:
                msg = await self.control_channel.wait_for_signal(timeout=0.1)
                if not msg:
                    continue
                
                if msg.signal == ControlSignal.INTERRUPT:
                    await self.handle_interruption(msg.metadata.get('text', ''))
            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Control loop error: {e}")
                break
    
    async def handle_interruption(self, text: str):
        """Handle barge-in interruption."""
        interrupt_start = datetime.now()
        
        can_interrupt = await self.fsm.can_interrupt()
        
        if not can_interrupt:
            self.log_event("INTERRUPT_DENIED", f"Cannot interrupt in state {self.fsm.state.value}")
            return
        
        self.log_event("INTERRUPT_HANDLE", "Processing interruption...")
        
        # Stop TTS immediately
        if self.is_speaking and self.speaking_task:
            self.is_speaking = False
            self.speaking_task.cancel()
            try:
                await self.speaking_task
            except asyncio.CancelledError:
                pass
        
        # ✅ FIX: Valid transition speaking -> interrupted
        await self.fsm.transition(ConversationState.INTERRUPTED, "User interrupted")
        
        # Then interrupted -> listening
        await self.fsm.transition(ConversationState.LISTENING, "Ready for new input")
        
        # Calculate barge-in latency
        barge_in_latency = (datetime.now() - interrupt_start).total_seconds() * 1000
        
        self.log_event(
            "BARGE_IN_COMPLETE",
            f"Latency: {barge_in_latency:.1f}ms"
        )
    
    async def stop(self):
        """Stop simulation."""
        if self.control_task:
            self.control_task.cancel()
            try:
                await self.control_task
            except asyncio.CancelledError:
                pass
        
        await self.telephony.disconnect()
        self.log_event("SYSTEM_STOP", "Orchestrator stopped")
    
    def print_summary(self):
        """Print simulation summary."""
        print("\n" + "="*80)
        print("📊 SIMULATION SUMMARY")
        print("="*80)
        
        print(f"\nTotal Events: {len(self.event_log)}")
        print(f"Duration: {self.event_log[-1]['elapsed_ms']:.0f}ms\n")
        
        print("Event Timeline:")
        print("-" * 80)
        for event in self.event_log:
            print(
                f"  {event['elapsed_ms']:6.0f}ms | "
                f"{event['fsm_state']:12s} | "
                f"{event['event_type']:15s} | "
                f"{event['details']}"
            )
        
        print("\n" + "="*80)
        
        # Validate barge-in
        barge_in_events = [e for e in self.event_log if e['event_type'] == 'BARGE_IN_COMPLETE']
        if barge_in_events:
            latency_str = barge_in_events[0]['details']
            latency_ms = float(latency_str.split(': ')[1].replace('ms', ''))
            
            if latency_ms < 100:
                print(f"✅ PASS: Barge-In latency {latency_ms:.1f}ms < 100ms")
            else:
                print(f"❌ FAIL: Barge-In latency {latency_ms:.1f}ms >= 100ms")
        
        # Check final state
        final_state = self.event_log[-1]['fsm_state']
        if final_state == 'listening':
            print(f"✅ PASS: Final state is LISTENING")
        else:
            print(f"❌ FAIL: Final state is {final_state}, expected LISTENING")
        
        print("="*80 + "\n")


async def run_barge_in_scenario():
    """
    Run barge-in test scenario:
    
    1. User says "Hola"
    2. System processes and starts speaking
    3. 500ms after speaking starts, user interrupts with "Espera, una duda"
    4. System should stop speaking immediately and return to LISTENING
    """
    print("\n" + "="*80)
    print("🧪 BARGE-IN SIMULATION TEST")
    print("="*80)
    print("\nScenario:")
    print("  1. User says 'Hola'")
    print("  2. System processes (300ms)")
    print("  3. System starts speaking")
    print("  4. At t=500ms: User interrupts 'Espera, una duda'")
    print("  5. System must stop speaking and return to LISTENING")
    print("\n" + "="*80 + "\n")
    
    orchestrator = SimulationOrchestrator()
    user = orchestrator.user
    
    try:
        # Start system
        await orchestrator.start()
        
        # Script user actions
        user.script_conversation([
            UserAction(delay_ms=100, action_type="speak", data="Hola"),
            UserAction(delay_ms=800, action_type="interrupt", data="Espera, una duda")
            # 100ms user speaks + 300ms processing + 500ms speaking = 900ms total delay
        ])
        
        # Execute scripted conversation
        user_task = asyncio.create_task(user.execute_script())
        
        # Wait for completion
        await user_task
        
        # Give system time to process final interrupt
        await asyncio.sleep(0.5)
        
        # Stop system
        await orchestrator.stop()
        
        # Print results
        orchestrator.print_summary()
    
    except Exception as e:
        logger.error(f"Simulation error: {e}", exc_info=True)
        await orchestrator.stop()


if __name__ == "__main__":
    print("\n🚀 Starting Barge-In Simulation...")
    asyncio.run(run_barge_in_scenario())
    print("\n✅ Simulation complete\n")
