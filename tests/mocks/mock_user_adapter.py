"""
Mock User Adapter - Simulates user behavior.

Injects audio/text events to test system responses.
"""
import asyncio
import logging
from typing import List, Tuple
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UserAction:
    """Represents a simulated user action."""
    delay_ms: int  # Delay from start or previous action
    action_type: str  # "speak", "silence", "interrupt"
    data: str  # Text content or audio signal
    

class MockUserAdapter:
    """
    Simulates user behavior for testing.
    
    Can inject:
    - Speech events (simulated audio/text)
    - Silence periods
    - Interruptions (barge-in)
    """
    
    def __init__(self, telephony_adapter):
        """
        Args:
            telephony_adapter: MockTelephonyAdapter to inject audio through
        """
        self.telephony = telephony_adapter
        self.actions: List[UserAction] = []
        self.start_time: Optional[datetime] = None
    
    def script_conversation(self, actions: List[UserAction]):
        """
        Script a sequence of user actions.
        
        Args:
            actions: List of UserAction to execute
            
        Example:
            user.script_conversation([
                UserAction(delay_ms=0, action_type="speak", data="Hola"),
                UserAction(delay_ms=2000, action_type="silence", data=""),
                UserAction(delay_ms=500, action_type="interrupt", data="Espera")
            ])
        """
        self.actions = actions
        logger.info(f"📝 [MockUser] Scripted {len(actions)} actions")
    
    async def execute_script(self):
        """
        Execute scripted conversation.
        
        Returns timestamps for each action executed.
        """
        if not self.actions:
            logger.warning("[MockUser] No actions scripted")
            return []
        
        self.start_time = datetime.now()
        timestamps = []
        
        for i, action in enumerate(self.actions):
            # Wait for scheduled delay
            await asyncio.sleep(action.delay_ms / 1000)
            
            timestamp = datetime.now()
            elapsed_ms = (timestamp - self.start_time).total_seconds() * 1000
            
            logger.info(
                f"👤 [MockUser] t={elapsed_ms:.0f}ms | "
                f"Action {i+1}/{len(self.actions)}: {action.action_type} | "
                f"Data: '{action.data}'"
            )
            
            # Execute action
            if action.action_type == "speak":
                await self._simulate_speech(action.data)
            elif action.action_type == "interrupt":
                await self._simulate_interrupt(action.data)
            elif action.action_type == "silence":
                # Just wait (already handled by delay)
                pass
            
            timestamps.append({
                'action': action.action_type,
                'data': action.data,
                'timestamp': timestamp,
                'elapsed_ms': elapsed_ms
            })
        
        logger.info(f"✅ [MockUser] Script execution complete")
        return timestamps
    
    async def _simulate_speech(self, text: str):
        """
        Simulate user speaking.
        
        Args:
            text: What user is saying
        """
        # Generate fake audio data (in real test, this would be actual audio bytes)
        # For now, we use text as marker
        audio_data = f"AUDIO:{text}".encode('utf-8')
        
        # Inject through telephony adapter
        await self.telephony.inject_incoming_audio(audio_data)
    
    async def _simulate_interrupt(self, text: str):
        """
        Simulate user interrupting (barge-in).
        
        Args:
            text: Interruption content
        """
        # Same as speech, but marked as interruption
        audio_data = f"INTERRUPT:{text}".encode('utf-8')
        await self.telephony.inject_incoming_audio(audio_data)
    
    def quick_conversation(self, initial_speech: str, interrupt_at_ms: int, interrupt_text: str):
        """
        Quick helper for barge-in test scenario.
        
        Args:
            initial_speech: First thing user says
            interrupt_at_ms: When to interrupt (from start)
            interrupt_text: What to say during interruption
        """
        self.script_conversation([
            UserAction(delay_ms=0, action_type="speak", data=initial_speech),
            UserAction(delay_ms=interrupt_at_ms, action_type="interrupt", data=interrupt_text)
        ])
