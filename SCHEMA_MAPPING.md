# Schema Mapping: Database <-> Backend <-> Frontend

Este documento detalla el flujo de datos para las tablas críticas y valida la integridad de los mapeos.

## 1. Tabla: `calls` (Historial de Llamadas)

| Columna BD | Modelo SQLAlchemy (`models.py`) | Backend Usage (`history_router.py`) | Frontend (`store.v2.js` / HTML template) | Validación |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `id = Column(Integer, ...)` | `Call.id` | `deleteSelectedCalls` (ids param) | ✅ Auto-increment |
| `session_id` | `session_id` | `Call.session_id` | No expuesto visiblemente (backend id) | ✅ Internal Use |
| `start_time` | `start_time` | `Call.start_time` | `{{ call.start_time.strftime('%Y-%m-%d %H:%M') }}` (server-side render) | ✅ Server Render |
| `end_time` | `end_time` | `Call.end_time` | `{{ call.end_time }}` | ✅ Server Render |
| `status` | `status` | `Call.status` | `<span class="badge ...">{{ call.status }}</span>` | ✅ Server Render |
| `client_type` | `client_type` | `Call.client_type` | usado para filtrar en `/rows` query | ✅ Filter Logic |
| `extracted_data` | `extracted_data` | `Call.extracted_data` | **NO USADO / NO VISIBLE** | ❌ **BROKEN** (Ver reporte) |

## 2. Tabla: `transcripts` (Contenido de Llamada)

| Columna BD | Modelo SQLAlchemy | Backend Usage | Frontend Usage | Validación |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `id` | - | - | ✅ |
| `call_id` | `call_id` | Foreign Key | - | ✅ |
| `role` | `role` | `Transcript.role` | - | ✅ |
| `content` | `content` | `Transcript.content` | **NO EXPUESTO en UI Historial** | ❌ **MISSING UI** |
| `timestamp` | `timestamp` | `Transcript.timestamp` | - | ✅ |

*Nota Crítica: La tabla `transcripts` existe en BD pero no se popula (ver Auditoría Pasada) y tampoco tiene una vista en el Frontend para ver el detalle de la conversación.*

## 3. Tabla: `agent_configs` (Configuración)

| Columna BD | Modelo SQLAlchemy | Pydantic Schema (`profile_config.py`) | Frontend (`store.v2.js`) | Validación |
| :--- | :--- | :--- | :--- | :--- |
| `voice_speed` | `voice_speed` | `voice_speed` | `this.c.voiceSpeed` | ✅ Direct mapping |
| `voice_speed_phone` | `voice_speed_phone` | `voice_speed` (via `get_profile('twilio')`) | `this.c.voiceSpeed` | ✅ Abstracted by Backend |
| `system_prompt` | `system_prompt` | `system_prompt` | `this.c.prompt` | ✅ Direct mapping |
| `interruption_threshold` | `interruption_threshold` | `interruption_threshold` | `this.c.interruptWords` | ⚠️ **Naming Drift** (threshold vs words) |

---

## Hallazgos
1.  **Server-Side Rendering (Jinja2)**: El historial se renderiza en el servidor (`history_rows.html`), por lo que no hay consumo JSON directo en `store.v2.js` para mostrar filas. Esto reduce el riesgo de inconsistencia de nombres de variables en JS, pero aumenta la opacidad.
2.  **Abstracción de Perfiles**: El backend usa `get_profile()` para mapear columnas con sufijo (`_phone`) a nombres genéricos (`voice_speed`) en el Pydantic schema. El Frontend recibe estos objetos genéricos en `initTwilioConfig()` etc. Esto es una arquitectura sólida.
3.  **Datos Muertos**: `extracted_data` y `transcripts` son invisibles para el usuario final actualmente.
