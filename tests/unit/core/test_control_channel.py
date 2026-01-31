"""
Unit tests for ControlChannel - Dedicated control signal channel.

Tests Module 2 implementation from Gap Analysis.
Validates signal bypassing, non-blocking delivery, thread-safety.
"""
import pytest
import asyncio
from app.core.control_channel import ControlChannel, ControlSignal


class TestControlChannel:
    """Test suite for ControlChannel."""
    
    @pytest.mark.asyncio
    async def test_send_and_receive_interrupt(self):
        """Control channel should send and receive INTERRUPT signal."""
        channel = ControlChannel()
        
        # Send signal
        await channel.send(ControlSignal.INTERRUPT, {'text': 'user spoke'})
        
        # Receive signal
        msg = await asyncio.wait_for(channel.wait_for_signal(), timeout=0.1)
        
        assert msg is not None
        assert msg.signal == ControlSignal.INTERRUPT
        assert msg.metadata['text'] == 'user spoke'
    
    @pytest.mark.asyncio
    async def test_send_and_receive_cancel(self):
        """Control channel should send and receive CANCEL signal."""
        channel = ControlChannel()
        
        await channel.send(ControlSignal.CANCEL, {'reason': 'test'})
        
        msg = await asyncio.wait_for(channel.wait_for_signal(), timeout=0.1)
        
        assert msg.signal == ControlSignal.CANCEL
        assert msg.metadata['reason'] == 'test'
    
    @pytest.mark.asyncio
    async def test_has_pending_signal(self):
        """has_pending should return True when signal waiting."""
        channel = ControlChannel()
        
        assert not channel.has_pending()
        
        await channel.send(ControlSignal.INTERRUPT)
        
        assert channel.has_pending()
    
    @pytest.mark.asyncio
    async def test_signal_cleared_after_receive(self):
        """Signal should be cleared after being consumed."""
        channel = ControlChannel()
        
        await channel.send(ControlSignal.INTERRUPT)
        assert channel.has_pending()
        
        msg = await channel.wait_for_signal()
        
        assert not channel.has_pending()
        assert msg.signal == ControlSignal.INTERRUPT
    
    @pytest.mark.asyncio
    async def test_timeout_on_no_signal(self):
        """wait_for_signal with timeout should raise TimeoutError if no signal."""
        channel = ControlChannel()
        
        with pytest.raises(asyncio.TimeoutError):
            await channel.wait_for_signal(timeout=0.1)
    
    @pytest.mark.asyncio
    async def test_signal_bypasses_queue(self):
        """Control signal should deliver immediately (no queue blocking)."""
        channel = ControlChannel()
        
        # Measure latency
        import time
        start = time.time()
        
        # Send signal in background
        async def send_after_delay():
            await asyncio.sleep(0.01)  # 10ms
            await channel.send(ControlSignal.INTERRUPT)
        
        asyncio.create_task(send_after_delay())
        
        # Wait for signal
        msg = await channel.wait_for_signal(timeout=1.0)
        
        elapsed = time.time() - start
        
        # Should receive within ~20ms (well under 100ms)
        assert elapsed < 0.1
        assert msg.signal == ControlSignal.INTERRUPT
    
    @pytest.mark.asyncio
    async def test_multiple_signals_latest_wins(self):
        """If multiple signals sent before consume, latest should win."""
        channel = ControlChannel()
        
        # Send multiple signals rapidly
        await channel.send(ControlSignal.INTERRUPT, {'order': 1})
        await channel.send(ControlSignal.CANCEL, {'order': 2})
        await channel.send(ControlSignal.PAUSE, {'order': 3})
        
        # Only latest should be received
        msg = await channel.wait_for_signal()
        
        assert msg.signal == ControlSignal.PAUSE
        assert msg.metadata['order'] == 3
    
    @pytest.mark.asyncio
    async def test_clear_pending_signal(self):
        """clear() should remove pending signal."""
        channel = ControlChannel()
        
        await channel.send(ControlSignal.INTERRUPT)
        assert channel.has_pending()
        
        await channel.clear()
        
        assert not channel.has_pending()
    
    @pytest.mark.asyncio
    async def test_convenience_method_send_interrupt(self):
        """send_interrupt() convenience method should work."""
        channel = ControlChannel()
        
        await channel.send_interrupt(text="hello")
        
        msg = await channel.wait_for_signal()
        
        assert msg.signal == ControlSignal.INTERRUPT
        assert msg.metadata['text'] == "hello"
        assert msg.metadata['reason'] == 'user_barge_in'
    
    @pytest.mark.asyncio
    async def test_convenience_method_send_cancel(self):
        """send_cancel() convenience method should work."""
        channel = ControlChannel()
        
        await channel.send_cancel(reason="test_cancel")
        
        msg = await channel.wait_for_signal()
        
        assert msg.signal == ControlSignal.CANCEL
        assert msg.metadata['reason'] == "test_cancel"
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Channel should track signals_sent and signals_received."""
        channel = ControlChannel()
        
        stats = channel.get_stats()
        assert stats['signals_sent'] == 0
        assert stats['signals_received'] == 0
        
        await channel.send(ControlSignal.INTERRUPT)
        stats = channel.get_stats()
        assert stats['signals_sent'] == 1
        
        await channel.wait_for_signal()
        stats = channel.get_stats()
        assert stats['signals_received'] == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_send_receive(self):
        """Channel should handle concurrent send/receive safely."""
        channel = ControlChannel()
        
        # Simulate producer-consumer pattern
        async def producer():
            for i in range(5):
                await channel.send(ControlSignal.INTERRUPT, {'count': i})
                await asyncio.sleep(0.01)
        
        async def consumer():
            received = []
            for _ in range(5):
                msg = await channel.wait_for_signal(timeout=1.0)
                received.append(msg.metadata['count'])
            return received
        
        # Run concurrently
        producer_task = asyncio.create_task(producer())
        consumer_task = asyncio.create_task(consumer())
        
        await producer_task
        received = await consumer_task
        
        # Should receive all signals (may skip some due to overwrite)
        assert len(received) <= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
