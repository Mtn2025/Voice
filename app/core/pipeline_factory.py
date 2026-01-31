"""
Pipeline Factory - Encapsulates pipeline construction logic.
Decouples the Orchestrator from concrete processor instantiation.
"""
import asyncio
import logging
from collections.abc import Callable
from typing import Any

from app.core.audio.hold_audio import HoldAudioPlayer

# Managers & Utils
from app.core.control_channel import ControlChannel
from app.core.managers import CRMManager

# Processors
from app.core.pipeline import Pipeline

# Ports
from app.domain.ports import LLMPort, STTPort, TTSPort

# Domain Logic (Use Cases)
from app.domain.use_cases import DetectTurnEndUseCase, ExecuteToolUseCase
from app.processors.logic.aggregator import ContextAggregator
from app.processors.logic.llm import LLMProcessor
from app.processors.logic.metrics import MetricsProcessor
from app.processors.logic.reporter import TranscriptReporter
from app.processors.logic.stt import STTProcessor
from app.processors.logic.tts import TTSProcessor
from app.processors.logic.vad import VADProcessor
from app.processors.output.audio_sink import PipelineOutputSink

logger = logging.getLogger(__name__)

class PipelineFactory:
    """
    Factory for creating configured Voice Pipelines.
    """

    @staticmethod
    async def create_pipeline(
        config: Any,
        stt_port: STTPort,
        llm_port: LLMPort,
        tts_port: TTSPort,
        control_channel: ControlChannel,
        conversation_history: list[dict[str, str]],
        initial_context_data: dict[str, Any],
        crm_manager: CRMManager | None,
        tools: dict[str, Any],
        stream_id: str,
        transcript_callback: Callable[[str, str], Any],
        orchestrator_ref: Any,  # Interface compliant with PipelineOutputSink expectation
        loop: asyncio.AbstractEventLoop
    ) -> Pipeline:
        """
        Builds and initializes the processing pipeline.

        Args:
            config: AgentConfig model
            stt_port: STT Provider
            llm_port: LLM Provider
            tts_port: TTS Provider
            control_channel: Signal channel
            conversation_history: Shared history list
            initial_context_data: Call context
            crm_manager: CRM Manager (optional)
            tools: Tool definitions
            stream_id: Unique trace ID
            transcript_callback: Callback for reporter events
            orchestrator_ref: Reference to orchestrator (for sink)
            loop: Asyncio loop

        Returns:
            Pipeline: Initialized pipeline instance
        """

        # 1. STT Processor
        # Injects control channel for out-of-band signaling
        stt = STTProcessor(
            provider=stt_port,
            config=config,
            loop=loop,
            control_channel=control_channel
        )
        await stt.initialize()

        # 2. VAD Processor
        # Injects strict domain use case for turn detection
        detect_turn_end = DetectTurnEndUseCase(
            silence_threshold_ms=getattr(config, 'silence_timeout_ms', 500)
        )
        vad = VADProcessor(
            config=config,
            detect_turn_end=detect_turn_end,
            control_channel=control_channel
        )

        # 3. Context Aggregator
        agg = ContextAggregator(
            config=config,
            conversation_history=conversation_history,
            llm_provider=llm_port  # Needed for semantic context analysis
        )

        # 4. LLM Processor
        # Prepare context data (CRM + Initial)
        context_data = initial_context_data.copy()
        if crm_manager and crm_manager.crm_context:
            context_data['crm'] = crm_manager.crm_context

        # Tool Use Case
        execute_tool_use_case = ExecuteToolUseCase(tools)

        # Hold Audio Player (for tool execution delays)
        hold_audio_player = HoldAudioPlayer()

        llm = LLMProcessor(
            llm_port=llm_port,
            config=config,
            conversation_history=conversation_history,
            context=context_data,
            execute_tool_use_case=execute_tool_use_case,
            trace_id=stream_id,
            hold_audio_player=hold_audio_player
        )

        # 5. TTS Processor
        tts = TTSProcessor(tts_port, config)

        # 6. Metrics Processor
        metrics = MetricsProcessor(config)

        # 7. Transcript Reporter
        reporter = TranscriptReporter(transcript_callback, role_label="assistant")

        # 8. Output Sink
        output_sink = PipelineOutputSink(orchestrator_ref)

        # Assemble Pipeline
        processors = [stt, vad, agg, llm, tts, metrics, reporter, output_sink]
        logger.info(f"🏭 [Factory] Pipeline assembled with {len(processors)} processors")

        return Pipeline(processors)
