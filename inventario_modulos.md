# Inventario de Módulos del Sistema
*Auditoría realizada el 2026-01-26*

## 1. Módulos Core (`app/core/`)
El corazón del sistema, encargado de la orquestación, configuración y manejo de estado.
- **`config.py`**: Gestión de variables de entorno y configuración global.
- **`orchestrator.py`**: Cerebro principal que coordina STT, LLM y TTS.
- **`audio_processor.py`**: Procesamiento de audio raw (buffer, conversión).
- **`redis_state.py`**: Gestión de estado distribuido con Redis (Escalabilidad A9).
- **`security_middleware.py`**: Headers de seguridad y protección CSRF.
- **`logging_config.py` / `secure_logging.py`**: Sistema de logs estructurados y sanitizados.

## 2. Servicios Externos (`app/services/`)
Abstracciones para interactuar con APIs de terceros.
- **`azure_speech.py`**: Cliente para Azure TTS y STT.
- **`baserow.py`**: Integración CRM con Baserow.
- **`telephony.py`**: Abstracción para control de llamadas (Twilio/Telnyx).
- **`webhook.py`**: Envío de datos a hooks externos (n8n/Make).
- **`db_service.py`**: Interacción con la base de datos PostgreSQL.

## 3. Procesadores (`app/processors/`)
Lógica de tubería (pipeline) para el flujo de conversación.
- **`logic/`**: Lógica de negocio (VAD, LLM, Metrics).
- **`output/`**: Sinks de salida (envío de audio a Telnyx/Twilio).

## 4. Proveedores LLM (`app/providers/`)
Implementaciones específicas de modelos de lenguaje.
- **`groq.py`**: Cliente de alta velocidad para Groq (Llama 3).
- **`azure_openai.py`**: Cliente para Azure OpenAI (GPT-4/3.5).
- **`azure.py`**: (Legacy/Alternative) implementación Azure general.

## 5. API Routes (`app/api/` & `app/routers/`)
Puntos de entrada HTTP/WebSocket.
- **`routers/dashboard.py`**:Endpoints para el panel de control (HTML + API interna).
- **`routers/system.py`**: Health checks y métricas del sistema.
- **`api/routes.py`**: Enrutador principal de la API v1.
- **`api/endpoints/`**: Controladores específicos (Twilio, Telnyx).

## 6. Base de Datos (`app/db/`)
Capa de persistencia.
- **`models.py`**: Definición de esquemas SQLAlchemy (`Call`, `Config`).
- **`database.py`**: Configuración de `engine` y `session`.

## 7. Dependencias Clave
- **FastAPI**: Framework web asíncrono.
- **SQLAlchemy 2.0**: ORM moderno.
- **Redis**: Caché y Pub/Sub.
- **Prometheus Client**: Métricas oservables.
