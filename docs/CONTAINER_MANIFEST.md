# Manifiesto de Contenedorización - Asistente Andrea

**Versión:** 2.0 (Docker-Ready)
**Fecha:** 8 Enero 2026
**Objetivo:** Despliegue en producción con cero errores y total trazabilidad.

---

## 1. Arquitectura de Servicios

El sistema se compone de 3 servicios orquestados mediante Docker Compose.

### 🏗️ Servicio Principal: `app` (Voice Orchestrator)
- **Imagen Base:** `python:3.11-slim` (Debian Bookworm)
- **Rol:** API Server (FastAPI) + WebSocket Handler + Business Logic.
- **Usuario de Ejecución:** `app` (UID: 1000) - **Non-Root** para seguridad.
- **Puertos:** `8000/tcp` (HTTP/WS).
- **Dependencias del Sistema (Runtime):**
    - `libasound2` (Audio subsytem para Azure Speech SDK)
    - `gstreamer1.0-*` (Codecs de audio)
    - `libuuid1` (Requerido por Azure SDK)
    - `ca-certificates` (Comunicación segura HTTPS/WSS)
    - `tzdata` (Timezones correctos en logs)

### 🗄️ Servicio Base de Datos: `db`
- **Imagen:** `postgres:15-alpine`
- **Rol:** Persistencia relacional (Llamadas, Transcripciones, Configuración).
- **Volumen:** `postgres_data` -> `/var/lib/postgresql/data`
- **Healthcheck:** `pg_isready -U ${POSTGRES_USER}`

### ⚡ Servicio Cache/State: `redis` (Nuevo en Fase 2)
- **Imagen:** `redis:7-alpine`
- **Rol:** Rate Limiting (SlowAPI), Cache de Inferencia, Estado Volátil.
- **Volumen:** `redis_data` -> `/data`
- **Persistencia:** AOF (Append Only File) activado.

---

## 2. Mapa de Variables de Entorno (.env)

Estas variables son **obligatorias** y deben inyectarse en tiempo de ejecución.

| Variable | Descripción | Ejemplo / Valor |
| :--- | :--- | :--- |
| **APP Core** | | |
| `ADMIN_API_KEY` | Llave maestra para Dashboard | `v4-secure-random-string` |
| `SESSION_SECRET_KEY`| Firma de cookies/sesiones | `long-random-string` |
| `LOG_LEVEL` | Nivel de detalle logs | `INFO` (Prod) / `DEBUG` (Dev) |
| **Base de Datos** | | |
| `POSTGRES_SERVER` | Hostname del servicio DB | `db` (en docker network) |
| `POSTGRES_PORT` | Puerto DB | `5432` |
| `POSTGRES_DB` | Nombre de la base de datos | `voice_db` |
| `POSTGRES_USER` | Usuario DB | `admin` |
| `POSTGRES_PASSWORD` | Contraseña DB | **[SECRET]** |
| **Servicios AI** | | |
| `AZURE_SPEECH_KEY` | API Key Azure Cognitive | **[SECRET]** |
| `AZURE_SPEECH_REGION`| Región Azure | `eastus` |
| `GROQ_API_KEY` | API Key LLM Groq | **[SECRET]** |
| **Telefonía** | | |
| `TELNYX_API_KEY` | API Key Telnyx | **[SECRET]** |
| `TELNYX_PUBLIC_KEY` | Para validar firmas Webhook | **[SECRET]** |
| `TWILIO_AUTH_TOKEN` | (Opcional) Twilio Auth | **[SECRET]** |

---

## 3. Estrategia de Construcción (Build Strategy)

El `Dockerfile` utiliza **Multi-Stage Build** para minimizar el tamaño final y asegurar consistencia.

### Etapa 1: Builder (`/build`)
- **Objetivo:** Compilar dependencias que requieren compiladores de C/C++/Rust.
- **Herramientas:** `gcc`, `g++`, `make`, `libssl-dev`, `libffi-dev`, `rustc`, `cargo`.
- **Acción:**
    1. Instala `pip` actualizado.
    2. Instala `azure-cognitiveservices-speech` (binario complejo).
    3. Instala resto de `requirements.txt`.
    4. Genera wheels compatibles en `/root/.local`.

### Etapa 2: Runtime (`/app`)
- **Objetivo:** Imagen limpia para ejecución.
- **Base:** `python:3.11-slim` (Sin compiladores = Menor superficie de ataque).
- **Acción:**
    1. Copia paquetes pre-compilados desde **Builder**.
    2. Instala librerías dinámicas (`.so`) necesarias (`libasound2`, `libuuid1`).
    3. Crea usuario `app`.
    4. Ejecuta `scripts/startup.sh`.

---

## 4. Ciclo de Vida de Inicio (Startup)

El script `startup.sh` garantiza la integridad antes de aceptar tráfico:

1.  **Wait-for-DB:** Script Python embebido que intenta conexión TCP/SQLAlchemy a la DB hasta 30 veces (timeout 60s).
2.  **Migraciones:** Ejecuta `alembic upgrade head` para sincronizar el esquema.
3.  **Inicio App:** Lanza `uvicorn` con 1 worker (modelo asíncrono eficiente).

---

## 5. Checklist de Despliegue

1.  [ ] **Clonar Repo:** `git clone ...`
2.  [ ] **Configurar Secretos:** Copiar `.env.example` -> `.env` y rellenar.
3.  [ ] **Build & Run:** `docker-compose up --build -d`
4.  [ ] **Verificar Logs:** `docker-compose logs -f app` (Buscar "Application startup complete").
5.  [ ] **Healthcheck:** `curl http://localhost:8000/health` -> `{"status":"ok"}`.

Este documento certifica que el entorno está completamente definido y listo para operar.
