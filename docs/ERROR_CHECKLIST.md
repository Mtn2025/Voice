# Registro de Errores Comunes y Checklist de Desbugueo

Este documento sirve como un checklist de primera respuesta para identificar y corregir errores recurrentes en el proyecto "Asistente Andrea".

## 1. Frontend - Interfaz Vacía o Controles Rotos

*   [ ] **Formato de Datos JSON (Backend -> Frontend)**:
    *   **Síntoma**: Dropdowns vacíos ("Seleccionar..."), listas no cargan.
    *   **Verificación**: ¿El backend envía objetos `{id: "x", name: "X"}` o solo strings `["x"]`? AlpineJS a menudo espera objetos para `customSelect`.
    *   **Solución**: Mapear strings a objetos en el router antes de enviar al template.

*   [ ] **Campos JSON en Formularios (Frontend -> Backend)**:
    *   **Síntoma**: Error 422 Unprocessable Entity al guardar configuración.
    *   **Verificación**: ¿Se están enviando strings vacíos `""` o literales `"{}"` para campos que el esquema Pydantic define como `dict` o `JSON`?
    *   **Solución**: Sanitizar en JS (`store.v2.js`) usando `JSON.parse()` o enviando `null` si está vacío.

*   [ ] **Dependencia de `alpine:init`**:
    *   **Síntoma**: La interactividad no funciona al cargar la página.
    *   **Verificación**: ¿Está el script `main.js` cargado como `type="module"`? ¿Se está registrando el store con `Alpine.data` antes de `Alpine.start()`?

## 2. Backend - Errores de API

*   [ ] **Discrepancia de Nombres de Campos (CamelCase vs SnakeCase)**:
    *   **Síntoma**: Los datos se guardan pero no aparecen al recargar, o no se guardan.
    *   **Verificación**: Revisar `FIELD_ALIASES` en los routers. El frontend suele usar camelCase (`voiceProvider`) y el modelo DB snake_case (`tts_provider`).

*   [x] **Endpoint de Campañas Faltante (Dead Code)**:
    *   **Síntoma**: Error 404 al intentar "Iniciar Campaña".
    *   **Causa**: El router `campaigns.py` no existe ni está montado en `main.py`.
    *   **Solución**: Crear `app/routers/campaigns.py` y registrarlo en `main.py`. (CORREGIDO)

*   [x] **Política de Credenciales (Diseño)**:
    *   **Nota**: Las credenciales sensibles (Twilio SID, Telnyx API Key) NO se guardan en la DB.
    *   **Estado**: Correcto (Configured via Environment). El Dashboard solo muestra estado, no permite edición.

*   [x] **Falta de Columnas SIP & Trunking**:
    *   **Síntoma**: Los campos SIP (URI, User, Pass) no se guardan.
    *   **Solución**: Agregar columnas a `agent_config` para configuración SIP dinámica. (CORREGIDO)

*   [ ] **Validación de Tipos Pydantic**:

*   [x] **Falta de Columnas System (Configuración de Gobierno)**:
*   [x] **Falta de Columnas Advanced (Calidad y Safety)**:
    *   **Síntoma**: Los campos Noise Suppression, Codec, Backchannel y Safety Limits no se guardan.
    *   **Solución**: Agregar columnas a `agent_configs`. (CORREGIDO)

*   [x] **Bug en Historial (Sorting)**:
    *   **Síntoma**: Error 500 al cargar historial (AttributeError: created_at).
    *   **Solución**: Cambiar ordenamiento a `Call.start_time`. (CORREGIDO)

*   [x] **Falta de Columnas Model (Temperatura)**:
    *   **Síntoma**: No se guarda la temperatura ni tokens.
    *   **Solución**: Agregar columnas a `agent_configs`. (CORREGIDO)


## 3. Infraestructura y Despliegue

*   [ ] **Exposición de Puertos Docker**:
    *   **Síntoma**: "Connection Refused" al intentar acceder a la API desde host o servicios externos.
    *   **Verificación**: ¿Está la sección `ports` definida en `docker-compose.yml` para el entorno/rama correcta?

*   [ ] **Variables de Entorno Faltantes**:
    *   **Síntoma**: Errores 500 al iniciar servicios externos (Azure, Twilio).
    *   **Verificación**: Confirmar que `.env` contiene todas las claves requeridas y que `app/core/config.py` las está leyendo.

*   [ ] **Docker Desktop / Daemon Apagado**:
    *   **Síntoma**: `npipe:////./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`.
    *   **Verificación**: Ejecutar `docker ps`. Si falla, Docker Desktop no está corriendo.
    *   **Solución**: Iniciar Docker Desktop manualmente.

## 4. Base de Datos

*   [ ] **Migraciones Pendientes**:
    *   **Síntoma**: `UndefinedColumn` o `RelationNotFound`.
    *   **Verificación**: Ejecutar `alembic current` vs `alembic heads`.
    *   **Solución**: Generar (`revision --autogenerate`) o aplicar (`upgrade head`) migraciones.

*   [ ] **Errores 500 por Variables no Definidas (`NameError`)**:
    *   **Síntoma**: Server Error tras un refactor. Log: `name 'X' is not defined`.
    *   **Verificación**: ¿Se borró accidentalmente un bloque de código necesario al reemplazar otro? (e.g. `models` en dashboard).
    *   **Solución**: Revisar el diff y restaurar el código faltante.

*   [ ] **Métodos Faltantes en Clases (`AttributeError`)**:
    *   **Síntoma**: `object has no attribute 'x'`. Común al delegar lógica entre componentes (ej. Sink -> Orchestrator).
    *   **Verificación**: ¿La clase contenedora expone el método que el componente hijo intenta llamar?
    *   **Solución**: Implementar el método "proxy" que delegue al gestor correspondiente.

*   [ ] **Desincronización de Base de Datos (Schema Drift)**:
    *   **Síntoma**: Error 500 `ProgrammingError: column "x" does not exist` aunque `alembic current` diga que está al día.
    *   **Causa**: Cambios manuales en Modelos sin generar migración, o migración fallida silenciosamente.
    *   **Solución**:
        1.  `docker compose exec app alembic revision --autogenerate -m "fix_drift"`
        2.  `docker compose exec app alembic upgrade head`

*   [ ] **Archivos Faltantes en Docker (Bind Mount Issues)**:
    *   **Síntoma**: `FileNotFoundError` en scripts que existen en local.
    *   **Causa**: Docker no está montando el volumen correctamente o la imagen no copió el archivo.


## 5. Deuda Técnica y Procesos (Código y Arquitectura)

*   [x] **Desalineación de Payloads Frontend-Backend (Silent Schema Ignorance)**:
    *   **Síntoma**: Errores silenciosos donde campos del frontend no se guardan en DB (Ignored).
    *   **Causa Técnica**: `BrowserConfigUpdate` y `TwilioConfigUpdate` filtraban campos no declarados explícitamente.
    *   **Solución**: Se auditaron todas las pestañas y se agregaron campos faltantes a los esquemas (incluyendo `tools_schema`, `crm_enabled` y campos `_phone` específicos). (CORREGIDO)

*   [x] **Bug de Doble Prefijo en API Routers (404 Not Found)**:
    *   **Síntoma**: Endpoints inaccesibles (`/api/config/twilio` devuelve 404).
    *   **Causa**: `main.py` añadía prefijos a routers que ya los tenían definidos internamente. Resultado: `/api/config/api/config/...`.
    *   **Solución**: Eliminación de prefijos redundantes en `main.py` y normalización de routers. (CORREGIDO)

*   [x] **Bloqueo de Lista Blanca en Config Utils**:
    *   **Síntoma**: Actualizaciones de perfil ignoraban cambios globales (como CRM o Tools) aunque el esquema los aceptara.
    *   **Causa**: `update_profile_config` filtraba claves globales contra una lista blanca estricta.
    *   **Solución**: Se añadieron `crm_enabled`, `tools_schema`, `tools_async` y otros a la `global_keys` whitelist. (CORREGIDO)

*   [x] **Campos Ignorados por FIELD_ALIASES Faltantes (Silent Ignore)** ✅ **RESUELTO**:
    *   **Síntoma**: Campos como `voicePitch`, `voiceVolume`, `voiceStyleDegree`, `contextWindow`, `toolChoice` se envían desde frontend pero no se guardan en DB.
    *   **Detección**: Script `verify_integral_gap_closure.py` reporta "Ignored (No DB Mapping)" aunque columnas DB existen.
    *   **Causa Raíz**: `FIELD_ALIASES` en `dashboard.py` no incluía mapeo camelCase → snake_case para estos campos.
    *   **Archivos Afectados**:
        - `app/routers/config_router.py` (endpoint secundario)
        - `app/routers/dashboard.py` (endpoint principal `/api/config/update-json`)
    *   **Solución Aplicada**:
        1. Agregados 3 aliases Voice en `config_router.py`:
           - `'voicePitch': 'voice_pitch'`
           - `'voiceVolume': 'voice_volume'`
           - `'voiceStyleDegree': 'voice_style_degree'`
        2. Agregados 6 aliases LLM en `dashboard.py`:
           - `'contextWindow': 'context_window'`
           - `'toolChoice': 'tool_choice'`
           - `'frequencyPenalty': 'frequency_penalty'`
           - `'presencePenalty': 'presence_penalty'`
           - `'dynamicVarsEnabled': 'dynamic_vars_enabled'`
           - `'dynamicVars': 'dynamic_vars'`
        3. Removidos defaults de Pydantic en `browser_schemas.py` (precaución)
    *   **Verificación**: ✅ `python tests/manual/verify_integral_gap_closure.py`
        - `contextWindow`: ✅ Persisted
        - `toolChoice`: ✅ Persisted
        - `voicePitch`: ✅ Persisted
        - Score final: **27/28 campos (96.4%)**
    *   **Nota**: Requirió rebuild completo (`docker-compose up --build`) para aplicar cambios en código Python.
    *   **Fecha**: 2026-02-07


## 6. Profile-Specific Fields (Telnyx/Twilio/Browser) - CRITICAL PATTERNS

### 🔥 PATRÓN COMÚN: "Campo no existe" aunque exists en DB y Model

**Síntoma Exacto**:
```
Response: {'status': 'success', 'updated': 0, 'normalized': 0, 'warnings': ['Campos ignorados (columna no existe): sttSilenceTimeout']}
```

**Detección Ultra-Rápida** (30 segundos):
```python
# 1. Verificar que columna existe en DB
docker-compose exec db psql -U postgres -d voice_db -c "SELECT column_name FROM information_schema.columns WHERE table_name='agent_configs' AND column_name='stt_silence_timeout_telnyx';"

# 2. Verificar que atributo existe en modelo Python
python -c "from app.db.models import AgentConfig; print(hasattr(AgentConfig, 'stt_silence_timeout_telnyx'))"

# 3. Si ambos = TRUE pero sigue failing → BUG DE SCHEMA PYDANTIC
```

**Root Causes Posibles** (en orden de frecuencia):

#### A. ❌ Campo faltante en Pydantic Schema (`*_schemas.py`) - **80% de casos**

**Síntoma**: 
- DB tiene columna ✅
- Model tiene atributo ✅  
- POST devuelve `updated: 0` o "columna no existe" ❌
- GET no devuelve el campo ❌

**Causa**: El campo NO está definido en `TelnyxConfigUpdate` / `TwilioConfigUpdate` / `BrowserConfigUpdate`

**Solución**:
```python
# En app/schemas/telnyx_schemas.py (o twilio/browser)
class TelnyxConfigUpdate(BaseConfig):
    # AGREGAR campo faltante con alias correcto:
    stt_silence_timeout_telnyx: int | None = Field(None, ge=200, le=5000, alias="sttSilenceTimeout")
    vad_threshold_telnyx: float | None = Field(None, alias="vadThreshold")
```

**Archivos a revisar**:
- `app/schemas/telnyx_schemas.py`
- `app/schemas/twilio_schemas.py`  
- `app/schemas/browser_schemas.py`

**Verificación**:
```bash
# Rebuild OBLIGATORIO (schema changes require reload)
docker-compose down
docker-compose up -d --build app
```

---

#### B. ❌ Alias faltante en FIELD_ALIASES (`dashboard.py`) - **15% de casos**

**Síntoma**:
- Schema tiene campo ✅
- DB tiene columna ✅
- POST devuelve `updated: 0` o "columna no existe" ❌

**Causa**: El POST endpoint no sabe mapear `sttSilenceTimeout` (frontend) → `stt_silence_timeout` (base)

**Solución**:
```python
# En app/routers/dashboard.py
FIELD_ALIASES = {
    # STT Configuration
    'sttProvider': 'stt_provider',
    'sttLang': 'stt_language',
    'sttModel': 'stt_model',  # ← AGREGAR
    'sttSilenceTimeout': 'stt_silence_timeout',  # ← AGREGAR
    'vadThreshold': 'vad_threshold',
    # ...
}
```

**Archivos a revisar**:
- `app/routers/dashboard.py` (líneas 37-160)
- `app/routers/config_router.py` (si existe FIELD_ALIASES secundario)

#### B2. ❌ Alias INCORRECTO (mapea a nombre base equivocado) - **Menos común**

**Síntoma**:
- Schema tiene campo ✅
- DB tiene columna ✅
- FIELD_ALIASES tiene entrada ✅
- POST devuelve `updated: 0` o "columna no existe" ❌

**Causa**: El alias existe pero mapea a nombre base incorrecto (ej: `'asyncTools': 'tools_async'` cuando debería ser `'asyncTools': 'async_tools'`)

**Detección**:
```bash
# 1. Verificar que alias existe
grep "asyncTools" app/routers/dashboard.py
# Output: 'asyncTools': 'tools_async',  ← EXISTE

# 2. Verificar nombre columna DB
python -c "from app.db.models import AgentConfig; print([a for a in dir(AgentConfig) if 'async_tools' in a])"
# Output: ['async_tools_telnyx']  ← Nombre base es async_tools NO tools_async

# 3. El alias mapea 'asyncTools' → 'tools_async' → 'tools_async_telnyx' (NO EXISTE ❌)
# 4. Debería mapear 'asyncTools' → 'async_tools' → 'async_tools_telnyx' (EXISTE ✅)
```

**Solución**:
```python
# En app/routers/dashboard.py
# ANTES (INCORRECTO):
'asyncTools': 'tools_async',

# DESPUÉS (CORRECTO):
'asyncTools': 'async_tools',
```

**Caso real**: Tab TOOLS - asyncTools (2026-02-07)

---

#### C. ❌ Inconsistencia camelCase vs snake_case en test/frontend - **5% de casos**

**Síntoma**:
- POST funciona ✅ (`updated: 1`)
- GET devuelve `None` ❌

**Causa**: Frontend/test usa `vad_threshold` pero API espera `vadThreshold`

**Detección**:
```python
# Verificar qué devuelve el GET
python -c "from dotenv import load_dotenv; import os, requests; load_dotenv(); key = os.getenv('ADMIN_API_KEY'); r = requests.get('http://localhost:8000/api/config?profile=telnyx', headers={'X-API-Key': key}); print([k for k in r.json() if 'vad' in k.lower()])"

# Si devuelve ['vad', 'vadThreshold'] → usar vadThreshold
# Si devuelve ['vad_threshold'] → usar vad_threshold
```

**Solución**: Actualizar test para usar key correcta (camelCase es estándar)

---

### 📋 Checklist de Diagnóstico Rápido (5 min)

Cuando veas `"Campos ignorados (columna no existe): X"`:

```bash
# PASO 1: ¿Existe en DB? (10 seg)
docker-compose exec db psql -U postgres -d voice_db -c "\d agent_configs" | findstr "campo_name"

# PASO 2: ¿Existe en Model? (5 seg)  
python -c "from app.db.models import AgentConfig; print([a for a in dir(AgentConfig) if 'campo_name' in a])"

# PASO 3: ¿Existe en Schema Pydantic? (30 seg)
# Buscar en app/schemas/*_schemas.py
grep -r "campo_name" app/schemas/*.py

# PASO 4: ¿Existe en FIELD_ALIASES? (30 seg)
grep "frontendKey" app/routers/dashboard.py app/routers/config_router.py

# PASO 5: Si 1 y 2 = SI, pero 3 o 4 = NO → AGREGAR y REBUILD
```

---

### 🛠️ Fix Aplicado: TRANSCRIBER Tab (2026-02-07)

**Contexto**: Tab TRANSCRIBER pasó de 18.2% → 100% tras encontrar este patrón

**Issues Encontrados**:
1. 9 campos STT faltaban en `telnyx_schemas.py` aunque existían en DB
2. 2 aliases faltaban en `dashboard.py` FIELD_ALIASES  
3. 1 test usaba snake_case en lugar de camelCase

**Archivos Modificados**:
```python
# app/schemas/telnyx_schemas.py (+9 campos)
stt_model_telnyx: str | None = Field(None, max_length=50, alias="sttModel")
stt_keywords_telnyx: list | dict | None = Field(None, alias="sttKeywords")
stt_silence_timeout_telnyx: int | None = Field(None, ge=200, le=5000, alias="sttSilenceTimeout")
stt_utterance_end_strategy_telnyx: str | None = Field(None, max_length=50, alias="sttUtteranceEnd")
stt_punctuation_telnyx: bool | None = Field(None, alias="sttPunctuation")
stt_smart_formatting_telnyx: bool | None = Field(None, alias="sttSmartFormatting")
stt_profanity_filter_telnyx: bool | None = Field(None, alias="sttProfanityFilter")
stt_diarization_telnyx: bool | None = Field(None, alias="sttDiarization")
stt_multilingual_telnyx: bool | None = Field(None, alias="sttMultilingual")

# app/routers/dashboard.py (+2 aliases)
'sttModel': 'stt_model',
'sttSilenceTimeout': 'stt_silence_timeout',
```

**Resultado**: ✅ 11/11 (100%) - TRANSCRIBER completamente funcional

**Tiempo Debug Total**: ~2 horas (se pudo reducir a 15 min con este checklist)

---

### ⚡ Quick Reference Commands

```bash
# Ver TODAS las columnas de un perfil en DB
docker-compose exec db psql -U postgres -d voice_db -c "SELECT column_name FROM information_schema.columns WHERE table_name='agent_configs' AND column_name LIKE '%_telnyx' ORDER BY column_name;"

# Ver TODOS los campos de un schema Pydantic
python -c "from app.schemas.telnyx_schemas import TelnyxConfigUpdate; print([f for f in TelnyxConfigUpdate.model_fields.keys()])"

# Ver TODOS los aliases de dashboard
grep "': '" app/routers/dashboard.py | head -50

# Test directo de un campo
python -c "from dotenv import load_dotenv; import os, requests; load_dotenv(); key = os.getenv('ADMIN_API_KEY'); r = requests.post('http://localhost:8000/api/config/update-json?profile=telnyx', json={'CAMPO': VALOR}, headers={'X-API-Key': key}); print(r.json()); r2 = requests.get('http://localhost:8000/api/config?profile=telnyx', headers={'X-API-Key': key}); print('GET:', r2.json().get('CAMPO'))"
```

---

