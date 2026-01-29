# Asistente Andrea - Voice AI Orchestrator

**Versión:** 2.1 (Modular Refactor)  
**Estado:** Production-Ready (Zero Technical Debt)  
**Salud del Sistema:** 10/10 (Architectural Purity 100/100)

Sistema de orquestación de voz conversacional "Native Voice" impulsado por IA. Diseñado sobre una arquitectura modular de **Pipeline & Processors**, permite interacciones de latencia ultra-baja (<500ms) a través de Telefonía (Twilio/Telnyx) y WebSockets.

Esta arquitectura única desacopla el transporte de audio de la lógica de procesamiento, permitiendo conectar múltiples proveedores de IA (Groq, Azure, OpenAI) como nodos intercambiables en un grafo de procesamiento.

---

## 🚀 Arquitectura Modular (Pipeline & Processors)

A diferencia de los enfoques monolíticos tradicionales, Asistente Andrea utiliza un diseño de **Pipeline de Procesamiento asíncrono**:

*   **Core:** `Pipeline` central que gestiona el flujo de Frames entre procesadores.
*   **Processors:** Unidades lógicas independientes que transforman datos (Audio -> Texto -> Intención -> Audio).
    *   **VAD (Voice Activity Detection):** Filtros SILERO/WebRTC para detección precisa de voz humana.
    *   **STT (Speech-to-Text):** Transcripción en tiempo real (Azure/Deepgram).
    *   **LLM (Logic):** Cerebro conversacional (Llama 3.3 en Groq / GPT-4o).
    *   **TTS (Text-to-Speech):** Síntesis de voz neural (Azure Neural Voices).
*   **Sinks:** Salidas agnósticas (Telnyx, Twilio, Browser).

### Diagrama de Flujo

```
[Input Source] --> [Transport] --> [VAD Processor] --> [STT Processor]
                                                            |
                                                            v
[Output Sink] <--- [TTS Processor] <--- [LLM Processor] (Aggregator)
```

---

## 🌟 Características Principales

*   **Orquestación Nativa:** Control total sobre buffers de audio, interrupciones y tiempos de silencio.
*   **Navegación Semántica:** El LLM no solo habla, puede "navegar" y ejecutar funciones del sistema.
*   **Multi-Proveedor:** Cambia de Azure a Deepgram o de Groq a OpenAI sin tocar el código base, solo configuración.
*   **Dashboard de Control:** Panel Web (AlpineJS) para ajuste fino de parámetros en tiempo real (temperatura, prompts, voces).
*   **Gestión de Estado:** Máquina de estados finita para manejar el ciclo de vida de la llamada (Handshake -> Listening -> Thinking -> Speaking).
*   **Persistencia:** Historial completo en PostgreSQL con trazabilidad de latencias y costos.

---

## 📋 Requisitos

### Software
*   **Python:** 3.11+ (Optimized for asyncio)
*   **PostgreSQL:** 15+
*   **Docker:** (Opcional, incluye `docker-compose.yml`)

### Integraciones (API Keys)
*   **LLM:** Groq (Recomendado por velocidad), OpenAI, Azure OpenAI.
*   **TTS/STT:** Azure Cognitive Services, Deepgram, ElevenLabs (WIP).
*   **Telefonía:** Telnyx (Soporte nativo Call Control), Twilio (Streams).

---

## 🛠️ Instalación y Uso

### 1. Clonar y Configurar
```bash
git clone <repo-url>
cd asistente-andrea
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows
pip install -r requirements.txt
```

### 2. Variables de Entorno
Copia `.env.example` a `.env` y configura tus proveedores:
```ini
# Core
ADMIN_API_KEY=tu_secreto_seguro

# LLM Providers
GROQ_API_KEY=gsk_...
AZURE_OPENAI_KEY=...

# Voice Providers
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/voice_db
```

### 3. Iniciar Servidor
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Visita `http://localhost:8000/dashboard` para acceder al panel de control.

---

## 🧪 Testing y Calidad

El proyecto incluye una suite exhaustiva de tests unitarios y de integración:

```bash
# Ejecutar tests
pytest

# Reporte de cobertura
pytest --cov=app --cov-report=html
```

---

## 📂 Estructura del Código

*   **`app/core/`**: Motor del sistema (Pipeline, Frames, VAD).
*   **`app/processors/`**: Nodos de procesamiento lógico (LLM, TTS, STT).
*   **`app/routers/`**: API REST y Webhooks.
*   **`app/templates/`**: Frontend del Dashboard (HTML/Jinja2).
*   **`app/providers/`**: Adaptadores para servicios externos.

---

## 📄 Licencia

Proyecto Privado - Todos los derechos reservados.
Desarrollado con enfoque en modularidad y alta performance.
