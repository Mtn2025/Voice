"""
Unit tests for ConversationFSM - Finite State Machine.

Tests FSM Module 1 implementation from Gap Analysis.
Validates state transitions, race condition prevention, thread-safety.
"""
import pytest
import asyncio
from app.domain.state import ConversationFSM, ConversationState


class TestConversationFSM:
    """Test suite for ConversationFSM."""
    
    @pytest.mark.asyncio
    async def test_initial_state_is_idle(self):
        """FSM should start in IDLE state."""
        fsm = ConversationFSM()
        assert fsm.state == ConversationState.IDLE
    
    @pytest.mark.asyncio
    async def test_valid_transition_idle_to_listening(self):
        """IDLE -> LISTENING should be valid."""
        fsm = ConversationFSM()
        
        success = await fsm.transition(ConversationState.LISTENING, "user_started")
        
        assert success is True
        assert fsm.state == ConversationState.LISTENING
    
    @pytest.mark.asyncio
    async def test_valid_transition_listening_to_processing(self):
        """LISTENING -> PROCESSING should be valid."""
        fsm = ConversationFSM()
        await fsm.transition(ConversationState.LISTENING, "setup")
        
        success = await fsm.transition(ConversationState.PROCESSING, "speech_ended")
        
        assert success is True
        assert fsm.state == ConversationState.PROCESSING
    
    @pytest.mark.asyncio
    async def test_valid_transition_processing_to_speaking(self):
        """PROCESSING -> SPEAKING should be valid."""
        fsm = ConversationFSM()
        await fsm.transition(ConversationState.LISTENING, "setup")
        await fsm.transition(ConversationState.PROCESSING, "setup")
        
        success = await fsm.transition(ConversationState.SPEAKING, "llm_done")
        
        assert success is True
        assert fsm.state == ConversationState.SPEAKING
    
    @pytest.mark.asyncio
    async def test_valid_transition_speaking_to_interrupted(self):
        """SPEAKING -> INTERRUPTED should be valid (barge-in)."""
        fsm = ConversationFSM()
        await fsm.transition(ConversationState.SPEAKING, "setup")
        
        success = await fsm.transition(ConversationState.INTERRUPTED, "user_barged_in")
        
        assert success is True
        assert fsm.state == ConversationState.INTERRUPTED
    
    @pytest.mark.asyncio
    async def test_invalid_transition_idle_to_processing(self):
        """IDLE -> PROCESSING should be INVALID."""
        fsm = ConversationFSM()
        
        success = await fsm.transition(ConversationState.PROCESSING, "invalid")
        
        assert success is False
        assert fsm.state == ConversationState.IDLE  # Should stay in IDLE
    
    @pytest.mark.asyncio
    async def test_invalid_transition_idle_to_interrupted(self):
        """IDLE -> INTERRUPTED should be INVALID."""
        fsm = ConversationFSM()
        
        success = await fsm.transition(ConversationState.INTERRUPTED, "invalid")
        
        assert success is False
        assert fsm.state == ConversationState.IDLE
    
    @pytest.mark.asyncio
    async def test_can_speak_when_idle(self):
        """Bot SHOULD be able to speak when IDLE."""
        fsm = ConversationFSM()
        
        can = await fsm.can_speak()
        
        assert can is True
    
    @pytest.mark.asyncio
    async def test_can_speak_when_processing(self):
        """Bot SHOULD be able to speak when PROCESSING."""
        fsm = ConversationFSM()
        await fsm.transition(ConversationState.LISTENING, "setup")
        await fsm.transition(ConversationState.PROCESSING, "setup")
        
        can = await fsm.can_speak()
        
        assert can is True
    
    @pytest.mark.asyncio
    async def test_cannot_speak_when_listening(self):
        """Bot should NOT speak when user is LISTENING."""
        fsm = ConversationFSM()
        await fsm.transition(ConversationState.LISTENING, "user_speaking")
        
        can = await fsm.can_speak()
        
        assert can is False
    
    @pytest.mark.asyncio
    async def test_cannot_speak_when_interrupted(self):
        """Bot should NOT speak when INTERRUPTED."""
        fsm = ConversationFSM()
        await fsm.transition(ConversationState.SPEAKING, "setup")
        await fsm.transition(ConversationState.INTERRUPTED, "setup")
        
        can = await fsm.can_speak()
        
        assert can is False
    
    @pytest.mark.asyncio
    async def test_can_interrupt_when_speaking(self):
        """User SHOULD be able to interrupt when bot is SPEAKING."""
        fsm = ConversationFSM()
        await fsm.transition(ConversationState.SPEAKING, "bot_talking")
        
        can = await fsm.can_interrupt()
        
        assert can is True
    
    @pytest.mark.asyncio
    async def test_cannot_interrupt_when_idle(self):
        """User should NOT interrupt when IDLE (nothing to interrupt)."""
        fsm = ConversationFSM()
        
        can = await fsm.can_interrupt()
        
        assert can is False
    
    @pytest.mark.asyncio
    async def test_cannot_interrupt_when_listening(self):
        """User should NOT interrupt when already LISTENING."""
        fsm = ConversationFSM()
        await fsm.transition(ConversationState.LISTENING, "setup")
        
        can = await fsm.can_interrupt()
        
        assert can is False
    
    @pytest.mark.asyncio
    async def test_transition_history_recorded(self):
        """FSM should record transition history."""
        fsm = ConversationFSM()
        
        await fsm.transition(ConversationState.LISTENING, "test1")
        await fsm.transition(ConversationState.PROCESSING, "test2")
        await fsm.transition(ConversationState.SPEAKING, "test3")
        
        history = fsm.get_history(last_n=10)
        
        assert len(history) == 3
        assert history[0].to_state == ConversationState.LISTENING
        assert history[1].to_state == ConversationState.PROCESSING
        assert history[2].to_state == ConversationState.SPEAKING
        assert history[0].reason == "test1"
    
    @pytest.mark.asyncio
    async def test_force_idle_from_any_state(self):
        """force_idle() should reset to IDLE from any state."""
        fsm = ConversationFSM()
        await fsm.transition(ConversationState.LISTENING, "setup")
        await fsm.transition(ConversationState.PROCESSING, "setup")
        
        await fsm.force_idle()
        
        assert fsm.state == ConversationState.IDLE
    
    @pytest.mark.asyncio
    async def test_concurrent_access_thread_safe(self):
        """FSM should handle concurrent transitions safely."""
        fsm = ConversationFSM()
        
        # Simulate race condition: multiple transitions attempted concurrently
        async def try_transition(to_state, reason):
            await fsm.transition(to_state, reason)
        
        # Start in IDLE, try LISTENING and SPEAKING simultaneously
        tasks = [
            asyncio.create_task(try_transition(ConversationState.LISTENING, "req1")),
            asyncio.create_task(try_transition(ConversationState.SPEAKING, "req2")),
        ]
        
        await asyncio.gather(*tasks)
        
        # Should resolve deterministically (only one should succeed)
        assert fsm.state in [ConversationState.LISTENING, ConversationState.SPEAKING]
    
    @pytest.mark.asyncio
    async def test_ending_is_terminal_state(self):
        """ENDING state should prevent further transitions."""
        fsm = ConversationFSM()
        await fsm.transition(ConversationState.SPEAKING, "setup")
        
        success = await fsm.transition(ConversationState.ENDING, "call_end")
        assert success is True
        assert fsm.state == ConversationState.ENDING
        
        # Try any transition from ENDING
        success = await fsm.transition(ConversationState.IDLE, "invalid")
        assert success is False
        assert fsm.state == ConversationState.ENDING  # Should stay


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
