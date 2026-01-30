"""
VoiceOrchestrator V2 - Clean Architecture Refactor

Responsibilities:
1. Manage WebSocket Connection (Input/Output)
2. Initialize and Host the Pipeline
3. Coordinate Managers (Audio, CRM, State)
4. Route Input Audio -> Pipeline
5. Lifecycle Management (start/stop)

Delegation:
- AudioManager: Audio streaming, queue, background audio
- CRMManager: Contact context, status updates
- Pipeline: Processing chain (STT -> VAD -> LLM -> TTS)
"""

import asyncio
import base64
import json
import logging
import time
from typing import Optional

from app.core.config import settings
# ✅ REMOVED: from app.services.db_service import db_service (Violation #1 FIXED)
# ✅ REMOVED: from app.db.database import AsyncSessionLocal (Violation #1 FIXED)

# Ports (Hexagonal Architecture)
from app.ports.transport import AudioTransport
from app.domain.ports import STTPort, LLMPort, TTSPort, ConfigRepositoryPort, CallRepositoryPort
from app.domain.ports import STTConfig, LLMRequest, TTSRequest
from app.domain.state import ConversationFSM, ConversationState  # ✅ FSM Module 1
from app.domain.use_cases import HandleBargeInUseCase, ExecuteToolUseCase  # ✅ Domain Use Cases

# Managers (NEW)
from app.core.managers import AudioManager, CRMManager
from app.core.control_channel import ControlChannel, ControlSignal  # ✅ Module 2

# Pipeline
from app.core.pipeline import Pipeline
from app.core.frames import (
    AudioFrame,
    TextFrame,
    CancelFrame,
    StartFrame,
    EndFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame
)

# Processors
from app.processors.logic.stt import STTProcessor
from app.processors.logic.vad import VADProcessor
from app.processors.logic.aggregator import ContextAggregator
from app.processors.logic.llm import LLMProcessor
from app.processors.logic.tts import TTSProcessor
from app.processors.logic.metrics import MetricsProcessor
from app.processors.output.audio_sink import PipelineOutputSink
from app.processors.logic.reporter import TranscriptReporter

logger = logging.getLogger(__name__)


class VoiceOrchestratorV2:
    """
    V2 Orchestrator with Clean Architecture.
    
    Delegates audio management to AudioManager.
    Delegates CRM operations to CRMManager.
    Focuses on pipeline coordination and lifecycle.
    """
    
    def __init__(
        self,
        transport: AudioTransport,
        stt_port: STTPort,  # ✅ Hexagonal Architecture - Inyectado
        llm_port: LLMPort,  # ✅ Hexagonal Architecture - Inyectado
        tts_port: TTSPort,  # ✅ Hexagonal Architecture - Inyectado
        config_repo: ConfigRepositoryPort,  # ✅ NEW - Injected
        call_repo: CallRepositoryPort,  # ✅ FIX VIOLATION #1 - Injected
        client_type: str = "twilio",
        initial_context: Optional[str] = None,
        tools: Optional[dict] = None  # ✅ Module 7: Tool Calling Infrastructure
    ) -> None:
        """
        Initialize Orchestrator V2 with Hexagonal Architecture.
        
        Args:
            transport: Audio transport interface (WebSocket wrapper)
            stt_port: Speech-to-Text provider (injected)
            llm_port: Large Language Model provider (injected)
            tts_port: Text-to-Speech provider (injected)
            config_repo: Configuration repository (injected) - ✅ REMOVES VIOLATION #1
            call_repo: Call record repository (injected) - ✅ FIX VIOLATION #1
            client_type: "browser", "twilio", or "telnyx"
            initial_context: Base64 encoded initial context from provider
        """
        # Transport & Config
        self.transport = transport
        self.client_type = client_type
        self.initial_context_token = initial_context
        self.initial_context_data = {}
        
        # Identifiers
        self.stream_id: Optional[str] = None
        self.call_db_id: Optional[int] = None
        
        # Configuration & State
        self.config = None
        self.conversation_history = []
        
        # Managers (Clean Architecture)
        self.audio_manager = AudioManager(transport, client_type)
        self.crm_manager: Optional[CRMManager] = None  # Initialized after config load
        
        # Pipeline
        self.pipeline: Optional[Pipeline] = None
        
        # ✅ Providers (Hexagonal - Injected via DI)
        self.stt = stt_port
        self.llm = llm_port
        self.tts = tts_port
        self.config_repo = config_repo  # ✅ Phase 1.2 - No more AsyncSessionLocal!
        self.call_repo = call_repo  # ✅ FIX VIOLATION #1 - Call repository abstraction
        
        # ✅ FSM Module 1 - Finite State Machine (Gap Analysis #1, #2, #3)
        self.fsm = ConversationFSM()
        
        # ✅ Control Channel Module 2 - Dedicated control signals (Gap Analysis #4)
        self.control_channel = ControlChannel()
        self._control_task: Optional[asyncio.Task] = None  # Background control loop
        
        # ✅ Domain Use Cases (Pure domain logic)
        self.barge_in_use_case = HandleBargeInUseCase()
        
        # ✅ Module 7: Tool Calling Infrastructure (Gap #7)
        self.tools = tools or {}  # Dict[str, ToolPort]
        self.execute_tool_use_case = ExecuteToolUseCase(self.tools)
        if self.tools:
            logger.info(f"🔧 [V2] Initialized with {len(self.tools)} tools: {list(self.tools.keys())}")
        
        # Event Loop
        self.loop = None
        
        # Lifecycle State
        self.start_time = time.time()
        self.last_interaction_time = time.time()
        self.monitor_task: Optional[asyncio.Task] = None
        self.active: bool = False  # ✅ Lifecycle State
        
        # Decode initial context if present
        if self.initial_context_token:
            try:
                decoded = base64.b64decode(self.initial_context_token).decode("utf-8")
                self.initial_context_data = json.loads(decoded)
                logger.info(f"📋 [V2] Decoded context: {list(self.initial_context_data.keys())}")
            except Exception as e:
                logger.warning(f"[V2] Failed to decode context: {e}")
    
    # -------------------------------------------------------------------------
    # LIFECYCLE MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def start(self) -> None:
        """Start all subsystems: Config -> CRM -> Pipeline -> Audio -> Monitor."""
        logger.info("🚀 [V2] Starting VoiceOrchestrator V2...")
        self.active = True  # ✅ Set active flag
        self.loop = asyncio.get_running_loop()
        
        # STEP 1: Load Configuration
        try:
            await self._load_config()
            logger.info("✅ [V2] Configuration loaded")
        except Exception as e:
            logger.error(f"❌ [V2] Config Load Failed: {e}")
            await self.stop()
            return
        
        # STEP 2: Initialize CRM Manager (requires config)
        try:
            self.crm_manager = CRMManager(self.config, self.initial_context_data)
            
            # Fetch CRM context if phone number available
            phone = self.initial_context_data.get('from') or self.initial_context_data.get('From')
            if phone:
                await self.crm_manager.fetch_context(phone)
                logger.info("✅ [V2] CRM context fetched")
        except Exception as e:
            logger.warning(f"⚠️ [V2] CRM initialization failed (non-blocking): {e}")
        
        # STEP 3: Build Pipeline
        try:
            await self._build_pipeline()
            logger.info("✅ [V2] Pipeline built")
        except Exception as e:
            logger.error(f"❌ [V2] Pipeline Build Failed: {e}")
            await self.stop()
            return
        
        # STEP 4: Start Pipeline
        try:
            await self.pipeline.start()
            logger.info("✅ [V2] Pipeline started")
        except Exception as e:
            logger.error(f"❌ [V2] Pipeline Start Failed: {e}")
            await self.stop()
            return
        
        # STEP 5: Start Audio Manager
        try:
            await self.audio_manager.start()
            logger.info("✅ [V2] AudioManager started")
        except Exception as e:
            logger.error(f"❌ [V2] AudioManager Start Failed: {e}")
            await self.stop()
            return
        
        # STEP 6: Send Initial Greeting (if configured)
        greeting_enabled = getattr(self.config, 'greeting_enabled', False)
        greeting_text = getattr(self.config, 'greeting_text', '')
        if greeting_enabled and greeting_text:
            logger.info("👋 [V2] Sending greeting")
            await self.pipeline.push_frame(TextFrame(text=greeting_text))
        
        # STEP 7: Start Control Loop (Module 2)
        try:
            self._control_task = asyncio.create_task(self._control_loop())
            logger.info("✅ [V2] Control loop started")
        except Exception as e:
            logger.error(f"❌ [V2] Control Loop Start Failed: {e}")
        
        # STEP 8: Start Idle Monitor
        self.monitor_task = asyncio.create_task(self._monitor_idle())
        
        logger.info("🚀 [V2] All subsystems running")
    
    async def stop(self):
        """Stop orchestrator and cleanup resources."""
        logger.info("[V2] Stopping orchestrator...")
        self.active = False
        
        # Cancel monitor task
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        # ✅ Module 2: Cancel control loop
        if self._control_task:
            self._control_task.cancel()
            try:
                await self._control_task
            except asyncio.CancelledError:
                pass
        
        # Stop pipeline
        if self.pipeline:
            await self.pipeline.stop()
        
        # Stop audio manager
        if self.audio_manager:
            await self.audio_manager.stop()
        
        # Update CRM status
        if self.crm_manager:
            phone = self.initial_context_data.get('from') or self.initial_context_data.get('From')
            await self.crm_manager.update_status(phone, "Call Ended")
        
        # ✅ FIX VIOLATION #1: Use CallRepositoryPort instead of AsyncSessionLocal
        if self.call_db_id:
            try:
                await self.call_repo.end_call(self.call_db_id)
                logger.info(f"✅ [V2] Call record {self.call_db_id} closed via repository")
            except Exception as e:
                logger.error(f"[V2] Failed to close DB record: {e}")
        
        logger.info("✅ [V2] Orchestrator stopped")
    
    # -------------------------------------------------------------------------
    # CONTROL LOOP (Module 2 - Dedicated Control Channel)
    # -------------------------------------------------------------------------
    
    async def _control_loop(self):
        """
        Background loop for processing control signals.
        
        ✅ Module 2: Dedicated control channel (bypasses data pipeline)
        Runs independently from pipeline queue to ensure immediate response.
        
        Handles:
            - INTERRUPT: User barge-in
            - CANCEL: Cancel current operation
            - EMERGENCY_STOP: Immediate shutdown
        """
        logger.info("[V2] Control loop started")
        
        while self.active:
            try:
                # Wait for control signal (non-blocking until signal arrives)
                msg = await self.control_channel.wait_for_signal(timeout=1.0)
                
                if not msg:
                    continue
                
                # Handle control signals
                if msg.signal == ControlSignal.INTERRUPT:
                    # User barge-in detected
                    text = msg.metadata.get('text', '')
                    await self.handle_interruption(text)
                
                elif msg.signal == ControlSignal.CANCEL:
                    # Cancel current operation
                    logger.info("[V2] CANCEL signal received")
                    await self._clear_pipeline_output()
                
                elif msg.signal == ControlSignal.EMERGENCY_STOP:
                    # Emergency shutdown
                    reason = msg.metadata.get('reason', 'unknown')
                    logger.warning(f"[V2] EMERGENCY_STOP: {reason}")
                    await self.stop()
                    break
                
                elif msg.signal == ControlSignal.CLEAR_PIPELINE:
                    # Clear queued frames
                    await self._clear_pipeline_output()
                
            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                continue
            
            except Exception as e:
                logger.error(f"[V2] Control loop error: {e}", exc_info=True)
        
        logger.info("[V2] Control loop stopped")
    
    # -------------------------------------------------------------------------
    # IDLE MONITORING
    # -------------------------------------------------------------------------
    
    async def process_audio(self, payload: str) -> None:
        """
        Process incoming audio from WebSocket.
        
        Args:
            payload: Base64 encoded audio data
        """
        if not self.pipeline:
            return
        
        try:
            # Decode audio
            audio_bytes = base64.b64decode(payload)
            if not audio_bytes:
                return
            
            # Push to pipeline
            sample_rate = 16000 if self.client_type == "browser" else 8000
            await self.pipeline.queue_frame(
                AudioFrame(data=audio_bytes, sample_rate=sample_rate, channels=1)
            )
            
            # Update last interaction time
            self.last_interaction_time = time.time()
            
        except Exception as e:
            logger.error(f"[V2] Error processing audio: {e}")
    
    async def handle_interruption(self, text: str = "") -> None:
        """
        Handle user interruption (barge-in).
        
        ✅ FSM Module 1: Validates state before interrupting (prevents race conditions)
        ✅ Hexagonal: Delegates to domain Use Case
        
        Args:
            text: Optional partial transcription causing interruption
        """
        # ✅ FSM Check: Only interrupt if bot is SPEAKING
        if not await self.fsm.can_interrupt():
            logger.debug(
                f"🛑 [V2] Interruption ignored - state={self.fsm.state.value} "
                f"(text: {text[:30] if text else 'VAD'})"
            )
            return
        
        logger.info(f"🛑 [V2] Interruption detected: {text[:50] if text else 'VAD'}")
        
        # ✅ FSM Transition: SPEAKING -> INTERRUPTED
        await self.fsm.transition(
            ConversationState.INTERRUPTED, 
            f"user_spoke: {text[:30]}" if text else "vad_detected"
        )
        
        # ✅ Execute domain Use Case (pure business logic)
        reason = f"user_spoke: {text[:30]}" if text else "vad_detected"
        command = self.barge_in_use_case.execute(reason)
        
        # ✅ Orchestrator ONLY coordinates (no business logic)
        if command.interrupt_audio:
            await self.audio_manager.interrupt_speaking()
        
        if command.clear_pipeline:
            await self._clear_pipeline_output()
        
        # ✅ FSM Transition: INTERRUPTED -> LISTENING
        await self.fsm.transition(ConversationState.LISTENING, "ready_for_input")
        
        # Update last interaction time
        self.last_interaction_time = time.time()
    
    # -------------------------------------------------------------------------
    # OUTPUT HANDLING (Audio to WebSocket) - DELEGATED TO AudioManager
    # -------------------------------------------------------------------------
    
    async def send_audio_chunked(self, audio_data: bytes) -> None:
        """
        Queue audio for transmission.
        
        DELEGATES to AudioManager for chunking and streaming.
        
        Args:
            audio_data: Raw audio bytes from TTS
        """
        await self.audio_manager.send_audio_chunked(audio_data)
        
        # Update last interaction time
        self.last_interaction_time = time.time()
    
    # -------------------------------------------------------------------------
    # MONITORING & TIMEOUTS
    # -------------------------------------------------------------------------
    
    async def _monitor_idle(self) -> None:
        """Monitor for idle timeout and max duration."""
        logger.info("👁️ [V2] Starting idle monitor")
        
        while True:
            try:
                await asyncio.sleep(1.0)
                now = time.time()
                
                # Max duration check
                max_duration = getattr(self.config, 'max_duration', 600)
                if now - self.start_time > max_duration:
                    logger.info("⏱️ [V2] Max duration reached")
                    await self.stop()
                    break
                
                # Idle timeout check (only if not speaking)
                if not self.audio_manager.is_bot_speaking:
                    idle_timeout = getattr(self.config, 'idle_timeout', 30)
                    if now - self.last_interaction_time > idle_timeout:
                        logger.info("😴 [V2] Idle timeout reached")
                        await self.stop()
                        break
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[V2] Monitor error: {e}")
    
    # -------------------------------------------------------------------------
    # CONFIGURATION & PIPELINE BUILDING
    # -------------------------------------------------------------------------
    
    async def _load_config(self):
        """
        Load agent configuration from repository.
        
        ✅ HEXAGONAL: Uses injected config_repo instead of direct DB access.
        ✅ RESOLVES VIOLATION #1: No more AsyncSessionLocal in core!
        """
        # Extract stream_id from context or generate new
        self.stream_id = self.initial_context_data.get('call_sid') or \
                       self.initial_context_data.get('stream_id') or \
                       self.initial_context_data.get('call_control_id')
        
        if not self.stream_id:
            import uuid
            self.stream_id = str(uuid.uuid4())
            logger.warning(f"[V2] No stream_id in context, generated: {self.stream_id}")
        
        # Get agent_id from context or use default
        agent_id = self.initial_context_data.get('agent_id', 1)
        
        # ✅ HEXAGONAL: Load configuration via repository port (NOT direct DB!)
        self.config = await self.config_repo.get_agent_config(agent_id)
        
        if not self.config:
            raise ValueError(f"Agent config not found for ID: {agent_id}")
        
        logger.info(f"[V2] Loaded config for agent: {self.config.name}")
        
        # Apply profile overlay (browser/twilio/telnyx specific config)
        self._apply_profile_overlay()
        
        # ✅ Providers already injected via DI - no initialization needed
        
        # Load background audio if configured
        self._load_background_audio()
    
    def _apply_profile_overlay(self):
        """Apply client-specific configuration overlays."""
        if self.client_type == "browser":
            # Browser optimizations
            self.config.voice_pacing_ms = 0  # No artificial pacing needed
            self.config.silence_timeout_ms = 1200  # Slightly more permissive
        elif self.client_type in ("twilio", "telnyx"):
            # Telephony defaults
            pacing = getattr(self.config, 'conversation_pacing_mode', 'normal')
            if pacing == 'fast':
                self.config.voice_pacing_ms = 200
                self.config.silence_timeout_ms = 800
            elif pacing == 'normal':
                self.config.voice_pacing_ms = 400
                self.config.silence_timeout_ms = 1000
            elif pacing == 'relaxed':
                self.config.voice_pacing_ms = 600
                self.config.silence_timeout_ms = 1500
    
    # ✅ _init_providers() REMOVED - Providers injected via DI in constructor
    
    def _load_background_audio(self):
        """Load background audio if configured."""
        bg_audio_enabled = getattr(self.config, 'bg_audio_enabled', False)
        if not bg_audio_enabled:
            return
        
        try:
            import os
            bg_path = getattr(self.config, 'bg_audio_path', 'assets/silence.wav')
            
            if os.path.exists(bg_path):
                with open(bg_path, 'rb') as f:
                    audio_data = f.read()
                
                # Decode WAV to raw PCM if needed
                # (Simplified - actual implementation would use AudioProcessor)
                self.audio_manager.set_background_audio(audio_data)
                logger.info(f"[V2] Background audio loaded: {bg_path}")
        except Exception as e:
            logger.warning(f"[V2] Failed to load background audio: {e}")
    
    async def _build_pipeline(self):
        """Build processing pipeline with all processors."""
        # Inject client context into config for processors
        if self.config:
            try:
                setattr(self.config, 'client_type', self.client_type)
            except Exception:
                pass
        
        # 1. STT Processor (uses STTPort)
        stt = STTProcessor(self.stt, self.config, self.loop, control_channel=self.control_channel) # ✅ Injected Out-of-Band Channel
        await stt.initialize()
        
        # 2. VAD Processor + ✅ P2: Inject DetectTurnEndUseCase (domain ownership)
        from app.domain.use_cases import DetectTurnEndUseCase
        vad = VADProcessor(
            config=self.config,
            detect_turn_end=DetectTurnEndUseCase(
                silence_threshold_ms=getattr(self.config, 'silence_timeout_ms', 500)
            ),
            control_channel=self.control_channel # ✅ Injected Out-of-Band Channel
        )
        
        # 3. Context Aggregator
        agg = ContextAggregator(
            self.config,
            self.conversation_history,
            llm_provider=self.llm
        )
        
        # 4. LLM Processor
        # Inject CRM context if available
        context_data = self.initial_context_data.copy()
        if self.crm_manager and self.crm_manager.crm_context:
            context_data['crm'] = self.crm_manager.crm_context
        
        # ✅ Module 10: Hold Audio Player (UX improvement)
        from app.core.audio.hold_audio import HoldAudioPlayer
        hold_audio_player = HoldAudioPlayer()
        
        llm = LLMProcessor(
            llm_port=self.llm,  # ✅ Module 9: LLMPort (hexagonal)
            config=self.config,
            conversation_history=self.conversation_history,
            context=context_data,
            execute_tool_use_case=self.execute_tool_use_case,  # ✅ Module 9: Tool calling
            trace_id=self.stream_id,  # ✅ Module 3: Distributed tracing
            hold_audio_player=hold_audio_player  # ✅ Module 10: Hold audio during tool execution
        )
        
        # 5. TTS Processor (uses TTSPort)
        tts = TTSProcessor(self.tts, self.config)  # ✅ TTSPort
        
        # 6. Metrics Processor
        metrics = MetricsProcessor(self.config)
        
        # 7. Transcript Reporter
        reporter = TranscriptReporter(self.stream_id, self.config)
        
        # 8. Output Sink
        output_sink = PipelineOutputSink(self)
        
        # Build pipeline chain
        processors = [stt, vad, agg, llm, tts, metrics, reporter, output_sink]
        
        self.pipeline = Pipeline(processors)
        logger.info(f"[V2] Pipeline built with {len(processors)} processors")
    
    async def _clear_pipeline_output(self):
        """Clear pending output from pipeline processors."""
        if not self.pipeline:
            return
        
        # Clear TTS processor queue
        for processor in self.pipeline._processors:
            if isinstance(processor, TTSProcessor):
                # TTS processor should have a method to clear its internal queue
                if hasattr(processor, 'clear_queue'):
                    await processor.clear_queue()
        
        # Clear audio manager queue
        await self.audio_manager.clear_queue()
        
        logger.debug("[V2] Pipeline output cleared")
    
    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    
    async def speak_direct(self, text: str):
        """
        Speak text directly, bypassing LLM.
        
        Args:
            text: Text to synthesize and speak
        """
        if not self.tts:
            logger.warning("[V2] TTS port not initialized")
            return
        
        try:
            # Use SynthesizeTextUseCase if available
            from app.use_cases.voice import SynthesizeTextUseCase
            from app.domain.value_objects import VoiceConfig
            
            voice_config = VoiceConfig.from_db_config(self.config)
            use_case = SynthesizeTextUseCase(self.tts)  # ✅ TTSPort
            
            frame = await use_case.execute(text, voice_config)
            # Handle AudioFrame (TTS output)
            if isinstance(frame, AudioFrame):
                # ✅ FSM Module 1: Check if allowed to speak
                if not await self.fsm.can_speak():
                    logger.debug(
                        f"[V2] Audio dropped - state={self.fsm.state.value} "
                        f"(prevents audio ghosting)"
                    )
                    return
                
                # ✅ FSM Transition: -> SPEAKING
                if self.fsm.state != ConversationState.SPEAKING:
                    await self.fsm.transition(ConversationState.SPEAKING, "tts_output_started")
                
                audio_data = frame.data
                await self.send_audio_chunked(audio_data)
            
        except Exception as e:
            logger.error(f"[V2] speak_direct failed: {e}")
