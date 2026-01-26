# Informe Preliminar: Evaluación de PipeCat
*Estado: NO IMPLEMENTADO*
*Fecha: 2026-01-26*

## 1. Análisis de Situación Actual
Actualmente, **Asistente Andrea** utiliza una arquitectura de orquestación personalizada (`VoiceOrchestrator` en `app/core/orchestrator.py`) construida sobre `FastAPI` y `WebSockets`.

- **Gestión de Audio**: Manual (`audio_processor.py`, `buffer`).
- **Pipeline**: Orquestación secuencial/paralela de VAD -> STT -> LLM -> TTS hecha a medida.
- **Conectividad**: Controladores directos para Twilio y Telnyx.

**Hallazgo**: No se encontraron referencias a la librería `pipecat-ai` ni similar en el código fuente actual.

## 2. ¿Qué es PipeCat?
PipeCat es un framework open-source para construir agentes de voz conversacionales en tiempo real. Abstrae la complejidad de manejar streams de audio y pipelines.

### Ventajas Potenciales (Migración)
1.  **Abstracción de Pipeline**: Manejo simplificado de VAD/Interrupciones.
2.  **Transport Layer**: Soporte nativo para WebRTC (Daily), WebSocket, Twilio.
3.  **Modularidad**: Cambiar de proveedor (ej: OpenAI Realtime API a Cartesia) es trivial.

### Desventajas / Riesgos
1.  **Refactorización Total**: Requeriría reescribir `VoiceOrchestrator` desde cero.
2.  **Pérdida de Control Fino**: Nuestra lógica actual de reintentos, prompts dinámicos y métricas custom está muy integrada.
3.  **Dependencia**: Añade una capa extra de abstracción que puede ocultar bugs.

## 3. Recomendación
La arquitectura actual es robusta y funcional. **No se recomienda migrar a PipeCat a corto plazo** (Fase 1/2) a menos que se requiera **WebRTC nativo** para reducir latencia extrema (<300ms).

Para la implementación actual (Telefónica/WebSocket), el orquestador actual es suficiente y ofrece mayor control.

**Estatus**: `OUT_OF_SCOPE` para el sprint actual.
