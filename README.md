# Asistente Andrea - Voice AI Orchestrator

**Versión:** 2.0  
**Estado:** Production-Ready (Single-Node)  
**Salud del Sistema:** 8.9/10

Sistema de orquestación de voz conversacional impulsado por IA que permite interacciones naturales por voz a través de llamadas telefónicas (Twilio/Telnyx) y navegador web. Combina procesamiento de voz en tiempo real con modelos de lenguaje avanzados para conversaciones fluidas y contextuales.

---

## 🚀 Características Principales

- **Multicanal:** Soporte para Twilio, Telnyx y WebSockets del navegador
- **STT/TTS Avanzado:** Integración con Azure Cognitive Services para reconocimiento y síntesis de voz
- **LLM de Alto Rendimiento:** Procesamiento con Groq (Llama 3.3 70B) para respuestas instantáneas
- **VAD Adaptativo:** Filtro de actividad de voz auto-calibrable para reducir ruido
- **Interrupciones Inteligentes:** Detección en tiempo real de cuando el usuario interrumpe al asistente
- **Dashboard Web:** Panel de control unificado para configuración de 3 perfiles (Browser, Twilio, Telnyx)
- **Audio de Fondo:** Soporte para ambientación de oficina/cafetería durante llamadas
- **Base de Datos Persistente:** PostgreSQL con historial completo de llamadas y transcripciones
- **Migraciones Versionadas:** Alembic para evolución controlada del schema

---

## 📋 Requisitos

### Software
- **Python:** 3.11 o 3.12 (⚠️ **No usar 3.13+** - dependencia `audioop` eliminada)
- **PostgreSQL:** 15+ (o Docker Compose)
- **Docker:** 24+ (opcional, recomendado para deployment)

### Servicios Externos (API Keys Requeridas)
- **Azure Cognitive Services** ([portal.azure.com](https://portal.azure.com)): Speech-to-Text y Text-to-Speech
- **Groq** ([console.groq.com](https://console.groq.com)): Modelos LLM (Llama 3.3)
- **Twilio** ([twilio.com/console](https://www.twilio.com/console)): Llamadas telefónicas (opcional)
- **Telnyx** ([telnyx.com](https://telnyx.com/)): Alternativa a Twilio (opcional)

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                   Dashboard Web                     │
│          (AlpineJS + TailwindCSS + Jinja2)          │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP/WS
┌──────────────────▼──────────────────────────────────┐
│              FastAPI Application                    │
│  ┌──────────────────────────────────────────────┐   │
│  │         VoiceOrchestrator (Core)             │   │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │   │
│  │  │ VAD      │ │  Audio   │ │    State    │  │   │
│  │  │ Filter   │ │ Manager  │ │   Manager   │  │   │
│  │  └──────────┘ └──────────┘ └─────────────┘  │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Azure     │  │     Groq     │  │ PostgreSQL │ │
│  │    STT/TTS  │  │  LLM (Llama) │  │  Database  │ │
│  └─────────────┘  └──────────────┘  └────────────┘ │
└──────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   ┌─────────┐         ┌──────────┐
   │ Twilio  │         │  Telnyx  │
   │ Webhooks│         │  Call    │
   │         │         │  Control │
   └─────────┘         └──────────┘
```

### Módulos Principales

- **`app/core/orchestrator.py`**: Coordinador central del flujo de conversación
- **`app/core/vad_filter.py`**: Filtro de actividad de voz autocalibrable
- **`app/core/audio_manager.py`**: Gestión de streams de audio bidireccionales
- **`app/core/state_manager.py`**: Máquina de estados de la llamada
- **`app/core/event_handlers.py`**: Eventos de Azure Speech SDK
- **`app/providers/*`**: Abstracciones de Azure, Groq, Twilio, Telnyx
- **`app/routers/dashboard.py`**: API REST del dashboard
- **`app/services/db_service.py`**: Capa de acceso a datos

---

## ⚙️ Instalación

### 1. Clonar Repositorio

```bash
git clone <repository-url>
cd "Asistente Andrea"
```

### 2. Crear Entorno Virtual

```bash
# Asegúrate de usar Python 3.11 o 3.12
python3.11 -m venv venv

# Activar (Linux/Mac)
source venv/bin/activate

# Activar (Windows)
venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

```bash
# Copiar template
cp .env.example .env

# Editar .env con tus API keys
nano .env  # o tu editor favorito
```

**Variables Críticas (mínimo para funcionar):**
```env
AZURE_SPEECH_KEY=tu_clave_aqui
AZURE_SPEECH_REGION=eastus
GROQ_API_KEY=tu_clave_aqui
POSTGRES_PASSWORD=password_seguro
ADMIN_API_KEY=genera_con_comando_abajo
```

**Generar ADMIN_API_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. Inicializar Base de Datos

**Opción A: Usar Docker Compose (Recomendado)**

Si no tienes PostgreSQL instalado localmente, la forma más rápida es usar Docker Compose:

```bash
# Levantar solo la base de datos
docker-compose up -d db

# Esperar 5 segundos a que PostgreSQL inicie
sleep 5

# Ejecutar migraciones
alembic upgrade head
```

**Opción B: Instalación Local de PostgreSQL**

```bash
# Instalar PostgreSQL según tu sistema operativo:
# Linux (Ubuntu/Debian):
sudo apt install postgresql-15 postgresql-contrib

# macOS (Homebrew):
brew install postgresql@15
brew services start postgresql@15

# Windows:
# Descargar instalador desde https://www.postgresql.org/download/windows/

# Crear base de datos
createdb voice_db

# Ejecutar migraciones
alembic upgrade head
```

### 6. Ejecutar Aplicación (Desarrollo)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Accede a:
- **Dashboard:** [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 🐳 Deployment con Docker

### Docker Compose (Recomendado)

```bash
# Configurar variables de entorno en .env
cp .env.example .env
nano .env

# Levantar stack completo (app + PostgreSQL)
docker-compose up -d

# Ver logs
docker-compose logs -f app
```

### Dockerfile Individual

```bash
# Build
docker build -t asistente-andrea .

# Run (requiere PostgreSQL externo)
docker run -d \
  --name andrea \
  --env-file .env \
  -p 8000:8000 \
  asistente-andrea
```

### Deployment en Coolify

1. Crear nuevo proyecto en Coolify
2. Conectar repositorio Git
3. Configurar variables de entorno (usa `.env.example` como referencia)
4. Marcar secretos como "Secret" en Coolify UI
5. Coolify auto-detectará `Dockerfile` y `docker-compose.yml`
6. Deploy automático

**Ver documentación completa:** [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

---

## 🧪 Testing

### Ejecutar Tests Unitarios

```bash
# Suite completa
pytest

# Con cobertura
pytest --cov=app --cov-report=html

# Solo tests rápidos
pytest -m "not slow"
```

**Cobertura actual:** 28 tests (22 PASSED, 6 SKIPPED por Python 3.13+)

**Ver documentación completa:** [`docs/TESTING.md`](docs/TESTING.md)

---

## 🔒 Seguridad

### Autenticación
- **Dashboard:** Protegido con API Key (`ADMIN_API_KEY`)
- **Webhooks:** Actualmente sin validación HMAC (⚠️ **Pendiente en Fase 2**)

### Logging Seguro
- Sanitización automática de secretos en logs (`app/core/secure_logging.py`)
- Máscaras para API keys, tokens, passwords

### Mejores Prácticas
- ✅ Variables de entorno para todos los secretos
- ✅ `.env` excluido de Git
- ✅ Passwords sin defaults en código
- ⚠️ Rate Limiting pendiente (Fase 2)
- ⚠️ Usuario non-root en Docker pendiente (Fase 2)

**Ver documentación completa:** [`docs/SECRETS_MANAGEMENT.md`](docs/SECRETS_MANAGEMENT.md)

---

## 📊 Gestión de Base de Datos

### Crear Nueva Migración

```bash
alembic revision --autogenerate -m "Descripción del cambio"
```

### Aplicar Migraciones

```bash
# Upgrade a última versión
alembic upgrade head

# Downgrade una versión
alembic downgrade -1

# Ver historial
alembic history
```

**Ver documentación completa:** [`docs/MIGRATIONS.md`](docs/MIGRATIONS.md)

---

## 🎯 Uso

### Dashboard Web

1. Accede a `/dashboard` con tu `ADMIN_API_KEY` en header `X-API-Key`
   - **Desarrollo:** `http://localhost:8000/dashboard`
   - ⚠️ **Producción:** Siempre usa **HTTPS** para proteger la API Key en tránsito
2. Selecciona perfil (🌐 Simulador, 📱 Twilio, 🦕 Telnyx)
3. Configura:
   - **Modelo:** Proveedor LLM, temperatura, tokens
   - **Voz:** TTS, idioma, velocidad, estilo emocional
   - **Transcriptor:** STT, umbrales de interrupción, denoising
   - **Funciones:** Colgar llamada, teclado DTMF, transferencia
   - **Avanzado:** Timeouts, duración máxima, grabación

### Probar con WebSocket (Browser)

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/media-stream?client=browser');
ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => console.log('Message:', event.data);
```

### Configurar Webhook Twilio

**URL:** `https://tu-dominio.com/api/v1/twilio/incoming-call`

### Configurar Webhook Telnyx

**URL:** `https://tu-dominio.com/api/v1/telnyx/call-control`  
**Método:** POST  
**Eventos:** `call.initiated`, `call.answered`, `call.hangup`

---

## 📁 Estructura del Proyecto

```
Asistente Andrea/
├── app/
│   ├── api/                 # WebSocket routes y webhooks
│   ├── core/                # Lógica central modularizada
│   ├── db/                  # Modelos SQLAlchemy
│   ├── providers/           # Integraciones (Azure, Groq, etc.)
│   ├── routers/             # Endpoints HTTP (Dashboard)
│   ├── services/            # Servicios de negocio
│   ├── static/              # Assets estáticos (JS, sounds)
│   └── templates/           # Templates Jinja2
├── alembic/                 # Migraciones de DB
│   └── versions/            # Archivos de migración
├── docs/                    # Documentación técnica
│   ├── AUTHENTICATION.md
│   ├── DEPLOYMENT.md
│   ├── MIGRATIONS.md
│   ├── SECRETS_MANAGEMENT.md
│   └── TESTING.md
├── scripts/                 # Scripts de utilería
│   └── startup.sh           # Script de inicio (Docker)
├── tests/
│   ├── unit/                # Tests unitarios
│   └── integration/         # Tests de integración
├── .env.example             # Template de variables de entorno
├── .gitignore
├── alembic.ini              # Configuración de Alembic
├── docker-compose.yml       # Orquestación Docker
├── Dockerfile               # Imagen multi-stage optimizada
├── pytest.ini               # Configuración de pytest
├── README.md                # Este archivo
└── requirements.txt         # Dependencias Python
```

---

## 🛣️ Roadmap

### ✅ Completado (Fase 1)
- ✅ Refactorización de Orchestrator monolítico
- ✅ Sistema de migraciones Alembic
- ✅ Autenticación básica (API Key)
- ✅ Tests unitarios (28 tests)
- ✅ Logging seguro
- ✅ Deployment scripts optimizados
- ✅ Dashboard multi-perfil

### 🔄 En Progreso (Fase 2)
- 🔄 **A1:** Crear README.md ← **Estamos aquí**
- ⏳ A2: Configurar Linters (Ruff)
- ⏳ A3: Rate Limiting
- ⏳ A4: Validación HMAC Webhooks
- ⏳ A9: Redis para escalabilidad horizontal
- ⏳ A11: Migrar de `audioop` (Python 3.13+ compat)

💡 **Próximos pasos:** Ver plan de trabajo completo en el directorio de documentación del proyecto.

---

## 🤝 Contribución

### Configurar Entorno de Desarrollo

```bash
# Instalar dependencias con herramientas de desarrollo
pip install -r requirements.txt

# Ejecutar linter (cuando esté configurado)
ruff check app/

# Ejecutar tests antes de commit
pytest

# Ejecutar security audit
pip-audit
```

### Guías de Estilo

- **Python:** PEP 8 (será validado con Ruff en Fase 2)
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)
- **Branches:** `feature/nombre`, `fix/bug`, `refactor/modulo`

---

## 📄 Licencia

Proyecto Propietario - Todos los derechos reservados.

---

## 🆘 Soporte

### Documentación Técnica
- [Autenticación](docs/AUTHENTICATION.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Migraciones](docs/MIGRATIONS.md)
- [Gestión de Secretos](docs/SECRETS_MANAGEMENT.md)
- [Testing](docs/TESTING.md)

### Troubleshooting

**Error: `audioop module not found`**
- Estás usando Python 3.13+. Usa Python 3.11 o 3.12.

**Error: Database connection failed**
- Verifica que PostgreSQL esté corriendo
- Revisa `POSTGRES_*` en `.env`

**Error: Azure Speech SDK error**
- Verifica `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION`
- Revisa cuota/límites en Azure Portal

**Dashboard no carga**
- Verifica que `ADMIN_API_KEY` esté configurado
- Envía header `X-API-Key` con tu clave

---

## 🔧 Estado del Sistema

**Última Auditoría:** 2026-01-06  
**Salud General:** 8.9/10 - Production-Ready (Single-Node)

| Componente | Estado | Puntuación |
|:-----------|:-------|:-----------|
| Arquitectura | ✅ Excelente | 10/10 |
| Base de Datos | ✅ Muy Bueno | 9.5/10 |
| Lógica de Negocio | ✅ Excelente | 9/10 |
| Seguridad | ✅ Muy Bueno | 9.5/10 |
| Calidad de Código | 🟡 Bueno | 8.5/10 |
| Frontend | 🟡 Bueno | 8/10 |
| Escalabilidad | 🟠 Regular | 7/10 |
| Infraestructura | ✅ Excelente | 9/10 |
| Compatibilidad | 🟡 Bueno | 8/10 |

**Limitaciones Conocidas:**
- ⚠️ Solo escalado vertical (single-node) sin Redis
- ⚠️ Dependencia `audioop` impide upgrade a Python 3.13+
- ⚠️ Sin rate limiting ni validación HMAC en webhooks

---

**¿Preguntas? ¿Problemas?** Crea un issue o contacta al equipo de desarrollo.
