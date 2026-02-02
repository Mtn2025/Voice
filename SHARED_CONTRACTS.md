# Shared Contracts: Generic Architecture

Este documento define los contratos y reglas que **SÍ** deben compartirse entre los tres perfiles (Simulador, Twilio, Telnyx).
Cualquier desviación de estos contratos por un perfil específico se considera una violación, a menos que esté explícitamente documentada en `ISOLATED_CONTRACTS.md`.

## 1. Reglas de Negocio (Core Domain)
Estas reglas aplican universalmente, sin importar el canal de comunicación.

| Regla | Descripción | Archivo / Componente | Validación Runtime |
| :--- | :--- | :--- | :--- |
| **Generación de Respuesta** | Todo input de usuario se procesa con el mismo `LLMProcessor`. El prompt system es base + overlays dinámicos. | `app/processors/logic/llm.py`<br>`app/core/prompt_builder.py` | Unit Test |
| **Manejo de Silencio** | El sistema debe detectar silencio para determinar el fin del turno del usuario (VAD). | `app/processors/logic/vad.py` | Configurable per profile |
| **Estructura de Pipeline** | STT -> VAD -> Aggregator -> LLM -> TTS. El orden es inmutable. | `app/core/pipeline_factory.py` | Integration Test |
| **Persistencia de Llamada** | Toda sesión genera un `CallRecord` (inicio) y finaliza con estado (fin), independientemente del transporte. | `app/domain/ports/call_repository_port.py` | Database Check |
| **Inyección de Contexto** | Todos los perfiles soportan inyección inicial de contexto (CRM, variables dinámicas). | `app/core/orchestrator_v2.py` | E2E Test |

## 2. Definición de Datos (Shared Models)
El esquema de datos es agnóstico al canal.

| Tipo de Dato | Schema | Uso |
| :--- | :--- | :--- |
| **Agent Config** | `AgentConfig` (SQLAlchemy) | Contiene configuraciones para todos los perfiles, pero usa columnas suffix (`_telnyx`) para valores aislados. El acceso es vía `config.get_profile(client_type)`. |
| **Transcripts** | `role: str`, `content: str` | Formato universal de historial. |
| **Tools** | JSON Schema (Function Definitions) | Las herramientas disponibles para el LLM son idénticas (agendar, consultar), salvo restricciones explícitas. |

## 3. Extracción Post-Llamada
El contrato de extracción define qué datos se deben intentar obtener al finalizar **cualquier** interacción.

**Schema Esperado (JSON):**
```json
{
  "summary": "Resumen de la conversación...",
  "intent": "agendar_cita | consulta | queja | irrelevante",
  "sentiment": "positive | neutral | negative",
  "extracted_entities": {
    "name": "Juan Perez",
    "phone": "+52...",
    "email": "juan@example.com",
    "appointment_date": "2023-10-25T10:00:00"
  },
  "next_action": "follow_up | none"
}
```
*Nota: Actualmente la implementación de esto está reportada como FALTANTE en `MINIMAL_FLOW.md`.*

## 4. Estructura Lógica de Pestañas (Dashboard)
Aunque la UI puede ocultar elementos (ver Isolated Contracts), la estructura lógica de configuración se comparte.

| Pestaña | Propósito Compartido |
| :--- | :--- |
| **General** | Nombre del agente, Prompt Principal (System Prompt). |
| **Voice** | Selección de Proveedor TTS, Voz, Estilo, Velocidad. (El catálogo de voces puede variar, pero el concepto es el mismo). |
| **Functions/Tools** | Definición de herramientas habilitadas. |
| **Advanced** | LLM Provider, Temperature, Max Tokens. |
