"""
VoiceOrchestrator V2 - Clean Architecture Refactor.

Manages WebSocket connections, pipeline initialization, and coordinates
managers (Audio, CRM) for voice interaction lifecycle.
"""

import asyncio
import base64
import contextlib
import json
import logging
import time
import uuid

from app.core.control_channel import ControlChannel, ControlSignal
from app.core.frames import (
    AudioFrame,
    TextFrame,
)
from app.core.managers import AudioManager, CRMManager
from app.core.pipeline import Pipeline
from app.core.pipeline_factory import PipelineFactory
from app.domain.config_logic import apply_client_overlay
from app.domain.ports import (
    AudioTransport,
    CallRepositoryPort,
    ConfigRepositoryPort,
    LLMPort,
    STTPort,
    TTSPort,
)
from app.domain.state import ConversationFSM, ConversationState
from app.domain.use_cases import ExecuteToolUseCase, HandleBargeInUseCase
from app.domain.value_objects import VoiceConfig
from app.use_cases.voice import SynthesizeTextUseCase

logger = logging.getLogger(__name__)


class VoiceOrchestratorV2:
    """
    V2 Orchestrator with Clean Architecture.

    Coallesces subsystem coordination:
    - Transport (Audio I/O)
    - Pipeline (Processing Chain)
    - Managers (Audio, CRM)
    """

    def __init__(
        self,
        transport: AudioTransport,
        stt_port: STTPort,
        llm_port: LLMPort,
        tts_port: TTSPort,
        config_repo: ConfigRepositoryPort,
        call_repo: CallRepositoryPort,
        client_type: str = "twilio",
        initial_context: str | None = None,
        tools: dict | None = None
    ) -> None:
        """
        Initialize Orchestrator.

        Args:
            transport: Audio transport interface
            stt_port: Speech-to-Text provider
            llm_port: Large Language Model provider
            tts_port: Text-to-Speech provider
            config_repo: Configuration repository
            call_repo: Call record repository
            client_type: "browser", "twilio", or "telnyx"
            initial_context: Base64 encoded context string
            tools: Dictionary of available tools
        """
        # Transport & Config
        self.transport = transport
        self.client_type = client_type
        self.initial_context_token = initial_context
        self.initial_context_data = {}

        # Identifiers
        self.stream_id: str | None = None
        self.call_db_id: int | None = None

        # Configuration & State
        self.config = None
        self.conversation_history = []

        # Managers
        self.audio_manager = AudioManager(transport, client_type)
        self.crm_manager: CRMManager | None = None

        # Pipeline
        self.pipeline: Pipeline | None = None

        # Providers (Injected via DI)
        self.stt = stt_port
        self.llm = llm_port
        self.tts = tts_port
        self.config_repo = config_repo
        self.call_repo = call_repo

        # Finite State Machine
        self.fsm = ConversationFSM()

        # Control Channel
        self.control_channel = ControlChannel()
        self._control_task: asyncio.Task | None = None

        # Domain Use Cases
        self.barge_in_use_case = HandleBargeInUseCase()

        # Tool Calling Infrastructure
        self.tools = tools or {}
        self.execute_tool_use_case = ExecuteToolUseCase(self.tools)
        if self.tools:
            logger.info(f"🔧 Initialized with {len(self.tools)} tools: {list(self.tools.keys())}")

        # Event Loop
        self.loop = None

        # Lifecycle State
        self.start_time = time.time()
        self.last_interaction_time = time.time()
        self.monitor_task: asyncio.Task | None = None
        self.active: bool = False

        # Decode initial context if present
        if self.initial_context_token:
            try:
                decoded = base64.b64decode(self.initial_context_token).decode("utf-8")
                self.initial_context_data = json.loads(decoded)
                logger.debug(f"📋 Decoded context keys: {list(self.initial_context_data.keys())}")
            except Exception as e:
                logger.warning(f"Failed to decode context: {e}")

    # -------------------------------------------------------------------------
    # LIFECYCLE MANAGEMENT
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start all subsystems: Config -> CRM -> Pipeline -> Audio -> Monitor."""
        logger.info("🚀 Starting VoiceOrchestrator...")
        self.active = True
        self.loop = asyncio.get_running_loop()

        # STEP 1: Load Configuration
        try:
            await self._load_config()
            logger.info("✅ Configuration loaded")
        except Exception as e:
            logger.error(f"❌ Config Load Failed: {e}")
            await self.stop()
            return

        # STEP 2: Initialize CRM Manager
        try:
            self.crm_manager = CRMManager(self.config, self.initial_context_data)

            # Fetch CRM context if phone number available
            phone = self.initial_context_data.get('from') or self.initial_context_data.get('From')
            if phone:
                await self.crm_manager.fetch_context(phone)
                logger.info("✅ CRM context fetched")
        except Exception as e:
            logger.warning(f"⚠️ CRM initialization failed (non-blocking): {e}")

        # STEP 3: Create Call Record
        try:
            if not self.call_db_id:
                call_record = await self.call_repo.create_call(
                    stream_id=self.stream_id,
                    client_type=self.client_type,
                    metadata=self.initial_context_data
                )
                self.call_db_id = call_record.id
                logger.info(f"✅ Call record created via repository: {self.call_db_id}")
        except Exception as e:
            logger.error(f"❌ Call Record Creation Failed: {e}")
            # Continue even if DB fails

        # STEP 4: Build Pipeline
        try:
            await self._build_pipeline()
            logger.info("✅ Pipeline built")
        except Exception as e:
            logger.error(f"❌ Pipeline Build Failed: {e}")
            await self.stop()
            return

        # STEP 5: Start Pipeline
        try:
            await self.pipeline.start()
            logger.info("✅ Pipeline started")
        except Exception as e:
            logger.error(f"❌ Pipeline Start Failed: {e}")
            await self.stop()
            return

        # STEP 6: Start Audio Manager
        try:
            await self.audio_manager.start()
            logger.info("✅ AudioManager started")
        except Exception as e:
            logger.error(f"❌ AudioManager Start Failed: {e}")
            await self.stop()
            return

        # STEP 7: Send Initial Greeting
        greeting_enabled = getattr(self.config, 'greeting_enabled', False)
        greeting_text = getattr(self.config, 'greeting_text', '')
        if greeting_enabled and greeting_text:
            logger.info("👋 Sending greeting")
            await self.pipeline.push_frame(TextFrame(text=greeting_text))

        # STEP 8: Start Control Loop
        try:
            self._control_task = asyncio.create_task(self._control_loop())
            logger.info("✅ Control loop started")
        except Exception as e:
            logger.error(f"❌ Control Loop Start Failed: {e}")

        # STEP 9: Start Idle Monitor
        self.monitor_task = asyncio.create_task(self._monitor_idle())

        logger.info("🚀 All subsystems running")

    async def stop(self) -> None:
        """Stop orchestrator and cleanup resources."""
        logger.info("Stopping orchestrator...")
        self.active = False

        # Cancel monitor task
        if self.monitor_task:
            self.monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.monitor_task

        # Cancel control loop
        if self._control_task:
            self._control_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._control_task

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

        # Close DB record
        if self.call_db_id:
            try:
                await self.call_repo.end_call(self.call_db_id)
                logger.info(f"✅ Call record {self.call_db_id} closed")
            except Exception as e:
                logger.error(f"Failed to close DB record: {e}")

        logger.info("✅ Orchestrator stopped")

    # -------------------------------------------------------------------------
    # CONTROL LOOP
    # -------------------------------------------------------------------------

    async def _control_loop(self) -> None:
        """
        Background loop for processing control signals.
        Runs independently from pipeline queue to ensure immediate response to
        Interrupts, Cancellations, and Emergency Stops.
        """
        logger.info("Control loop started")

        while self.active:
            try:
                # Wait for control signal (non-blocking until signal arrives)
                msg = await self.control_channel.wait_for_signal(timeout=1.0)

                if not msg:
                    continue

                # Handle control signals
                if msg.signal == ControlSignal.INTERRUPT:
                    text = msg.metadata.get('text', '')
                    await self.handle_interruption(text)

                elif msg.signal == ControlSignal.CANCEL:
                    logger.info("CANCEL signal received")
                    await self._clear_pipeline_output()

                elif msg.signal == ControlSignal.EMERGENCY_STOP:
                    reason = msg.metadata.get('reason', 'unknown')
                    logger.warning(f"EMERGENCY_STOP: {reason}")
                    await self.stop()
                    break

                elif msg.signal == ControlSignal.CLEAR_PIPELINE:
                    await self._clear_pipeline_output()

            except TimeoutError:
                continue

            except Exception as e:
                logger.error(f"Control loop error: {e}", exc_info=True)

        logger.info("Control loop stopped")

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
                AudioFrame(
                    data=audio_bytes, 
                    sample_rate=sample_rate, 
                    channels=1,
                )
            )

            # [TRACING] Log Audio Packet In
            logger.debug(f"🎤 [AUDIO_IN] Packet Trace | Size: {len(audio_bytes)} bytes | Stream: {self.stream_id}")

            # Update last interaction time
            self.last_interaction_time = time.time()

        except Exception as e:
            logger.error(f"Error processing audio: {e}")

    async def handle_interruption(self, text: str = "") -> None:
        """
        Handle user interruption (barge-in).

        Args:
            text: Optional partial transcription causing interruption
        """
        # Only interrupt if bot is SPEAKING/PROCESSING (Use Case Logic)
        if not await self.fsm.can_interrupt():
            logger.debug(
                f"🛑 Interruption ignored - state={self.fsm.state.value} "
                f"(text: {text[:30] if text else 'VAD'})"
            )
            return

        logger.info(f"🛑 Interruption detected: {text[:50] if text else 'VAD'}")

        # Transition: SPEAKING -> INTERRUPTED
        await self.fsm.transition(
            ConversationState.INTERRUPTED,
            f"user_spoke: {text[:30]}" if text else "vad_detected"
        )

        # Execute domain Use Case
        reason = f"user_spoke: {text[:30]}" if text else "vad_detected"
        command = self.barge_in_use_case.execute(reason)

        if command.interrupt_audio:
            await self.audio_manager.interrupt_speaking()

        if command.clear_pipeline:
            await self._clear_pipeline_output()

        # Transition: INTERRUPTED -> LISTENING
        await self.fsm.transition(ConversationState.LISTENING, "ready_for_input")

        # Update last interaction time
        self.last_interaction_time = time.time()

    # -------------------------------------------------------------------------
    # AUDIO & OUTPUT HANDLING
    # -------------------------------------------------------------------------

    async def send_audio_chunked(self, audio_data: bytes) -> None:
        """
        Queue audio for transmission via AudioManager.

        Args:
            audio_data: Raw audio bytes from TTS
        """
        await self.audio_manager.send_audio_chunked(audio_data)
        self.last_interaction_time = time.time()

    async def speak_direct(self, text: str) -> None:
        """
        Speak text directly, bypassing LLM.

        Args:
            text: Text to synthesize and speak
        """
        if not self.tts:
            logger.warning("TTS port not initialized")
            return

        try:
            voice_config = VoiceConfig.from_db_config(self.config)
            use_case = SynthesizeTextUseCase(self.tts)

            frame = await use_case.execute(text, voice_config)

            if isinstance(frame, AudioFrame):
                # Check FSM permissions
                if not await self.fsm.can_speak():
                    logger.debug(
                        f"Audio dropped - state={self.fsm.state.value} "
                        f"(prevents audio ghosting)"
                    )
                    return

                # Update State if needed
                if self.fsm.state != ConversationState.SPEAKING:
                    await self.fsm.transition(ConversationState.SPEAKING, "tts_output_started")

                audio_data = frame.data
                await self.send_audio_chunked(audio_data)

        except Exception as e:
            logger.error(f"speak_direct failed: {e}")

    # -------------------------------------------------------------------------
    # CONFIGURATION & FACTORY
    # -------------------------------------------------------------------------

    async def _load_config(self) -> None:
        """Load agent configuration from repository."""
        # Extract stream_id
        self.stream_id = (
            self.initial_context_data.get('call_sid') or
            self.initial_context_data.get('stream_id') or
            self.initial_context_data.get('call_control_id')
        )

        if not self.stream_id:
            self.stream_id = str(uuid.uuid4())
            logger.warning(f"No stream_id in context, generated: {self.stream_id}")

        # Get agent_id
        agent_id = self.initial_context_data.get('agent_id', 1)

        # Load config via repo
        self.config = await self.config_repo.get_agent_config(agent_id)

        if not self.config:
            raise ValueError(f"Agent config not found for ID: {agent_id}")

        logger.info(f"Loaded config for agent: {self.config.name}")

        # Apply client overlay
        apply_client_overlay(self.config, self.client_type)

        # Load background audio
        self._load_background_audio()

    def _load_background_audio(self) -> None:
        """Load background audio if configured."""
        bg_audio_enabled = getattr(self.config, 'bg_audio_enabled', False)
        if not bg_audio_enabled:
            return

        bg_path = getattr(self.config, 'bg_audio_path', 'assets/silence.wav')
        self.audio_manager.load_background_audio(bg_path)

    async def _build_pipeline(self) -> None:
        """Build processing pipeline using Factory."""
        if self.config:
            with contextlib.suppress(Exception):
                self.config.client_type = self.client_type

        self.pipeline = await PipelineFactory.create_pipeline(
            config=self.config,
            stt_port=self.stt,
            llm_port=self.llm,
            tts_port=self.tts,
            control_channel=self.control_channel,
            conversation_history=self.conversation_history,
            initial_context_data=self.initial_context_data,
            crm_manager=self.crm_manager,
            tools=self.tools,
            stream_id=self.stream_id,
            transcript_callback=self._handle_transcript,
            orchestrator_ref=self,
            loop=self.loop
        )
        logger.info("Pipeline built via PipelineFactory")

    async def _handle_transcript(self, role: str, text: str) -> None:
        """
        Handle transcript events from the reporter.
        Sends JSON event to the client (Browser/Simulator).
        """
        if self.client_type == "browser":
            try:
                msg = {
                    "type": "transcript",
                    "role": role,
                    "text": text
                }
                if hasattr(self.transport, 'send_json'):
                    await self.transport.send_json(msg)
            except Exception as e:
                logger.error(f"Failed to send transcript: {e}")

    async def _clear_pipeline_output(self) -> None:
        """Clear pending output from pipeline processors."""
        if not self.pipeline:
            return

        # Iterate processors and clear queues safely
        if hasattr(self.pipeline, '_processors'):
            for processor in self.pipeline._processors:
                if hasattr(processor, 'clear_queue'):
                    await processor.clear_queue()

        # Clear audio manager queue
        await self.audio_manager.clear_queue()

        logger.debug("Pipeline states cleared")

    async def _monitor_idle(self) -> None:
        """Monitor for idle timeout and max duration."""
        logger.info("👁️ Starting idle monitor")

        while True:
            try:
                await asyncio.sleep(1.0)
                now = time.time()

                # Max duration check
                max_duration = getattr(self.config, 'max_duration', 600)
                if now - self.start_time > max_duration:
                    logger.info("⏱️ Max duration reached")
                    await self.stop()
                    break

                # Idle timeout check (only if not speaking)
                if not self.audio_manager.is_bot_speaking:
                    idle_timeout = getattr(self.config, 'idle_timeout', 30)
                    if now - self.last_interaction_time > idle_timeout:
                        logger.info("😴 Idle timeout reached")
                        await self.stop()
                        break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
