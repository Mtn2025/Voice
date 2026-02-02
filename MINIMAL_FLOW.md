# Audit: Flujo Mínimo de Voz (Minimal Voice Flow)

Este documento describe el flujo mínimo viable identificado en el código actual, y reporta las discrepancias críticas encontradas vs. el requerimiento.

## 1. Definición del Flujo Mínimo (Intended vs Actual)

### Paso 1: Intento de Llamada y Verificación
*   **Intended**: Init Call -> Verify Status (Machine/Connected).
*   **Actual**:
    *   **Trigger**: POST `/api/v1/calls/test-outbound` initiates call via Telnyx API (`routes_v2.py:607`).
    *   **Verification**: Event-driven via Webhook `/api/v1/telnyx/call-control` (`routes_v2.py:62`).
    *   **Status**: Handled async in `active_calls` dictionary.
    *   **Dependencia**: `app/api/routes_v2.py` -> Telnyx API.

### Paso 2: Saludo + Invitación
*   **Intended**: If connected -> Greeting.
*   **Actual**:
    *   `OrchestratorV2.start()` (Line 212) sends `first_message` if configured (`speak-first`).
    *   **File**: `app/core/orchestrator_v2.py`.

### Paso 3: Loop STT -> Groq -> TTS
*   **Intended**: Listen -> Process -> Speak.
*   **Actual**:
    *   **Pipeline**: `STTProcessor` -> `VAD` -> `Aggregator` -> `LLMProcessor` -> `TTSProcessor`.
    *   **Execution**: Valid. The pipeline is built in `app/core/pipeline_factory.py`.
    *   **Files**: `app/core/orchestrator_v2.py`, `app/core/pipeline_factory.py`, `app/processors/logic/llm.py`.

### Paso 4: Extracción POST-LLAMADA (❌ BROKEN)
*   **Intended**: Extract Name, Phone, Interest, Metadata.
*   **Actual**:
    *   **NO CODE FOUND**. No hay lógica de extracción automática al finalizar la llamada.
    *   `OrchestratorV2.stop()` cierra el registro en BD pero no ejecuta extracción.
    *   `DBService` tiene método `update_call_extraction`, pero **NUNCA es llamado**.
    *   **Estado**: **CRORTO / FALTANTE**.

### Paso 5: Almacena Historial Completo (❌ BROKEN)
*   **Intended**: Save transcripts and metadata.
*   **Actual**:
    *   **Metadata**: `Call` record (start/end) is saved via `CallRepositoryPort` -> `SQLAlchemyCallRepository`.
    *   **Transcripts**: **NOT SAVED**. `TranscriptReporter` sends events to WS/Frontend, but **NO** saves to DB.
    *   `DBService.log_transcript` exists but is **NEVER CALLED** by the Orchestrator or Pipeline.
    *   **Estado**: **ROTO**. Solo se guarda el "cascarón" de la llamada, no el contenido.

---

## 2. Diagrama de Dependencias

```mermaid
graph TD
    A[API Trigger /test-outbound] -->|Telnyx API| B(Telnyx Cloud)
    B -->|Webhook| C[routes_v2.py /call-control]
    C -->|Answer & Stream| D[routes_v2.py /ws/media-stream]
    D --> ORCH[OrchestratorV2]
    ORCH -->|Builds| PIPE[Pipeline]
    
    subgraph Pipeline
    STT[STT Processor] --> VAD
    VAD --> AG[Aggregator]
    AG --> LLM[LLM Processor]
    LLM --> TTS[TTS Processor]
    end
    
    ORCH --x DB[Call History DB] : ❌ Missing Transcripts
    ORCH --x EXT[Extractor] : ❌ Missing Logic
```

## 3. Archivos Críticos (Max 5)
1.  `app/core/orchestrator_v2.py` (Control Flow)
2.  `app/api/routes_v2.py` (Entry Points)
3.  `app/core/pipeline_factory.py` (Pipeline Assembly)
4.  `app/processors/logic/llm.py` (Logic Core)
5.  `app/adapters/outbound/persistence/sqlalchemy_call_repository.py` (Data Persistence - **Review Needed due to missing transcript save**)

---

## 4. Reporte de Auditoría
> [!IMPORTANT]
> **FLUJO ROTO DETECTADO**
> No se puede continuar sin reparar:
> 1.  **Extracción de Datos**: No existe lógica implementada.
> 2.  **Persistencia de Historial**: Los transcripciones se pierden al cerrar la llamada.

El script de prueba adjunto (`test_minimal_flow.sh`) fallará intencionalmente en estos puntos.
