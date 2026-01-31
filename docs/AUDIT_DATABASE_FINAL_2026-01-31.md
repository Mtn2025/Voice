# AUDITORÍA EXHAUSTIVA DE BASE DE DATOS - INFORME FINAL

**Proyecto**: Asistente Andrea  
**Fecha**: 31 de Enero, 2026  
**Metodología**: Trazabilidad Completa con Simulación Gradual  
**Estado**: ✅ COMPLETADA (Fases 1-3 de 6)

---

## 📊 RESUMEN EJECUTIVO

Se completó una auditoría exhaustiva de las **353 columnas** en `AgentConfig` con trazabilidad completa Frontend → Schema → DB. Los resultados revelan:

- ✅ **95.4% sincronización Schema-DB** (188/197 campos)
- 🔴 **9 columnas faltantes** (requieren migración)
- ❌ **163 columnas obsoletas** (46% del total sin uso en schemas)

---

## 📋 RESULTADOS POR FASE

### Fase 1: Inventario Maestro ✅

**Total Columnas**: 353

**Distribución por Perfil**:
```
Browser (sin sufijo):   121 columnas
Phone (_phone):          99 columnas
Telnyx (_telnyx):       117 columnas
Global (compartidas):    14 columnas
Meta (id, name, etc):     2 columnas
```

**Salida**: `audit/inventory_353_columns.csv`

---

### Fase 2: Schema → Model Mapping ✅

**Sincronización por Perfil**:

| Perfil | Matched | Missing | Sync Rate |
|--------|---------|---------|-----------|
| **Browser** | 51 | 0 | 100% ✅ |
| **Phone** | 55 | 4 | 93.2% |
| **Telnyx** | 82 | 5 | 94.3% |
| **TOTAL** | **188** | **9** | **95.4%** ✅ |

**Salida**: `audit/schema_to_model_mapping.json`

---

### Fase 3: Clasificación de Columnas ✅

#### ✅ **Columnas VÁLIDAS**: 188 (53.3%)

Columnas que existen en DB Y están en schemas activos.

**Muestra**:
- `voice_speed` (browser)
- `voice_speed_phone` (phone)
- `voice_speed_telnyx` (telnyx)
- `system_prompt_phone` (phone)
- `llm_model_telnyx` (telnyx)

#### 🔴 **Columnas FALTANTES**: 9 (2.5%)

Campos definidos en schemas pero **SIN columna** en base de datos.

**Lista Completa**:

**Phone Profile** (4):
1. `response_length_phone`
2. `conversation_tone_phone`
3. `conversation_formality_phone`  
4. `conversation_pacing_phone`

**Telnyx Profile** (5):
1. `response_length_telnyx`
2. `conversation_tone_telnyx`
3. `conversation_formality_telnyx`
4. `conversation_pacing_telnyx`
5. `client_tools_enabled_telnyx`

**Impacto**: 🔴 **CRÍTICO**
- Usuarios pueden intentar guardar estos campos desde UI
- Datos SE PIERDEN silenciosamente (no hay columna para almacenar)

**Acción Requerida**: Crear migración Alembic

#### ❌ **Columnas OBSOLETAS**: 163 (46.2%)

Columnas que existen en DB pero **NO** están en ningún schema activo.

**Muestra (primeras 20)**:
1. `extraction_model` (global)
2. `stt_model` (browser)
3. `stt_keywords` (browser)
4. `stt_silence_timeout` (browser)
5. `stt_utterance_end_strategy` (browser)
6. `stt_punctuation` (browser)
7. `stt_profanity_filter` (browser)
8. `stt_smart_formatting` (browser)
9. `stt_diarization` (browser)
10. `stt_multilingual` (browser)
11. `temperature` (browser)
12. `first_message_mode` (browser)
13. `background_sound` (browser)
14. `idle_timeout` (browser)
15. `idle_message` (browser)
16. `max_duration` (browser)
17. `inactivity_max_retries` (browser)
18. `enable_denoising` (browser)
19. `pronunciation_dictionary` (browser)
20. `enable_end_call` (browser)

**Total**: 163 columnas obsoletas (lista completa en `audit/columns_classified.json`)

**Análisis**:
- ⚠️ **Posible Causa**: Migraciones de `ProfileConfigSchema` a schemas separados dejó muchas columnas sin mapeo
- ⚠️ **Riesgo**: Desperdicio de espacio en DB + confusión en mantenimiento
- ✅ **Oportunidad**: Limpieza de 46% de columnas

**Acciones Posibles**:
1. **Opción A** (Conservador): Agregar al schema apropiado si son necesarias
2. **Opción B** (Recomendado): Crear migración para eliminar columnas sin uso
3. **Opción C** (Híbrido): Revisar caso por caso

---

## 📋 MATRIZ DE TRAZABILIDAD (Muestra)

### Browser Profile

| Column | Type | Schema Field | Alias | Status |
|--------|------|--------------|-------|--------|
| `voice_speed` | Float | voice_speed | voiceSpeed | ✅ VALID |
| `voice_pitch` | Integer | voice_pitch | voicePitch | ✅ VALID |
| `llm_model` | String | llm_model | model | ✅ VALID |
| `temperature` | Float | - | - | ❌ OBSOLETE |
| `stt_model` | String | - | - | ❌ OBSOLETE |

### Phone Profile

| Column | Type | Schema Field | Alias | Status |
|--------|------|--------------|-------|--------|
| `voice_speed_phone` | Float | voice_speed_phone | voiceSpeed | ✅ VALID |
| `system_prompt_phone` | Text | system_prompt_phone | prompt | ✅ VALID |
| `response_length_phone` | - | response_length_phone | responseLength | 🔴 MISSING |
| `conversation_tone_phone` | - | conversation_tone_phone | conversationTone | 🔴 MISSING |
| `stt_model_phone` | String | - | - | ❌ OBSOLETE |

### Telnyx Profile

| Column | Type | Schema Field | Alias | Status |
|--------|------|--------------|-------|--------|
| `llm_model_telnyx` | String | llm_model_telnyx | model | ✅ VALID |
| `voice_speed_telnyx` | Float | voice_speed_telnyx | voiceSpeed | ✅ VALID |
| `response_length_telnyx` | - | response_length_telnyx | responseLength | 🔴 MISSING |
| `client_tools_enabled_telnyx` | - | client_tools_enabled_telnyx | clientToolsEnabled | 🔴 MISSING |
| `stt_model_telnyx` | String | - | - | ❌ OBSOLETE |

---

## 🎯 HALLAZGOS CRÍTICOS

### 🔴 Hallazgo #1: Columnas Faltantes (9)

**Severidad**: CRÍTICA  
**Impacto**: Pérdida silenciosa de datos

**Campos conversation_***:
- Los usuarios pueden configurar "Response Length", "Tone", "Formality", "Pacing" desde UI
- Schema valida correctamente
- **PERO** no hay columna DB para guardar

**Campo client_tools_enabled_telnyx**:
- Schema define habilitación de herramientas cliente
- Sin columna DB, valor no persiste

**Recomendación**: Crear migración inmediata

---

### ⚠️ Hallazgo #2: 163 Columnas Obsoletas (46%)

**Severidad**: MEDIA  
**Impacto**: Desperdicio de recursos, confusión en mantenimiento

**Posibles Causas**:
1. Refactor de `ProfileConfigSchema` a schemas separados (browser/twilio/telnyx)
2. Campos legacy de versiones anteriores
3. Campos creados por migraciones pero nunca usados

**Categorías de Obsoletos**:
- **STT Fields** (stt_model, stt_keywords, stt_punctuation, etc): ~10 campos browser + ~10 phone + ~10 telnyx
- **LLM Fields** (temperature, context_window, frequency_penalty): ~5 browser
- **Behavior** (idle_timeout, max_duration, first_message_mode): ~8 browser
- **Advanced** (pronunciation_dictionary, enable_end_call, transfer_phone_number): ~15 browser
- ... y ~115 más

**Recomendación**: Revisión caso por caso con stakeholders

---

### ✅ Hallazgo #3: Separación Hexagonal Correcta

**Severidad**: BAJA (positivo)  
**Impacto**: Arquitectura conforme a estándares

Los schemas separados (`browser_schemas.py`, `twilio_schemas.py`, `telnyx_schemas.py`) mantienen correctamente la separación hexagonal. El commit `32b204b` resolvió violaciones previas.

---

## 📋 PLAN DE ACCIÓN

### 🚨 Acción Inmediata (Prioridad 1)

**Crear Migración para Columnas Faltantes**

```python
# alembic/versions/xxxxx_add_missing_conversation_columns.py

def upgrade():
    # Phone Profile
    op.add_column('agent_configs', sa.Column('response_length_phone', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_tone_phone', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_formality_phone', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_pacing_phone', sa.String(50), nullable=True))
    
    # Telnyx Profile
    op.add_column('agent_configs', sa.Column('response_length_telnyx', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_tone_telnyx', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_formality_telnyx', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('conversation_pacing_telnyx', sa.String(50), nullable=True))
    op.add_column('agent_configs', sa.Column('client_tools_enabled_telnyx', sa.Boolean(), nullable=True, default=False))

def downgrade():
    # Reverse operations
    op.drop_column('agent_configs', 'response_length_phone')
    # ... resto de columnas
```

**Tiempo Estimado**: 30 minutos  
**Riesgo**: BAJO (solo agregar columnas, no eliminar)

---

### ⚠️ Acción de Corto Plazo (Prioridad 2)

**Revisar Columnas Obsoletas**

1. **Auditoría Manual** (2-3 horas):
   - Revisar cada una de las 163 columnas obsoletas
   - Determinar si son legacy o necesarias
   - Consultar con stakeholders

2. **Decisión por Columna**:
   - **Mantener + Agregar a Schema**: Si se usa en código backend directo
   - **Eliminar de DB**: Si confirmadamente obsoleta
   - **Documentar**: Si es campo interno (no user-facing)

3. **Crear Migración de Limpieza**:
   - Solo después de aprobación manual
   - Hacer backup antes de aplicar

---

### 📊 Acción de Largo Plazo (Prioridad 3)

**Normalización de Base de Datos**

Las 353 columnas en una sola tabla (`AgentConfig`) alcanzan los límites prácticos del modelo estrella.

**Propuesta**: Normalizar en v3.0

```
agent_config (id, name, created_at)
  ├─ agent_config_global (llm_provider, stt_provider, etc)
  ├─ agent_config_browser (voice_speed, llm_model, etc)
  ├─ agent_config_phone (voice_speed_phone, system_prompt_phone, etc)
  └─ agent_config_telnyx (voice_speed_telnyx, llm_model_telnyx, etc)
```

**Beneficios**:
- Queries más eficientes
- Mantenimiento más simple
- Escalabilidad mejorada

---

## 📊 MÉTRICAS FINALES

| Métrica | Valor Actual | Meta | Estado |
|---------|--------------|------|--------|
| Total Columnas | 353 | <250 (largo plazo) | ⚠️ Alto |
| Columnas Válidas | 188 (53%) | >90% | ⚠️ Bajo |
| Sincronización Schema-DB | 95.4% | >95% | ✅ OK |
| Columnas Faltantes | 9 | 0 | 🔴 Crítico |
| Columnas Obsoletas | 163 (46%) | <10% | 🔴 Crítico |

---

## ✅ CONCLUSIÓN Y RECOMENDACIONES

### Fortalezas
- ✅ Separación hexagonal correcta entre perfiles
- ✅ Alta sincronización Schema-DB (95.4%)
- ✅ Schemas bien documentados con aliases

### Debilidades
- 🔴 9 columnas faltantes causan pérdida silenciosa de datos
- 🔴 163 columnas obsoletas (46% del total)
- ⚠️ Modelo muy grande (353 columnas)

### Recomendaciones Prioritarias

**1. Inmediato** (Esta semana):
   - Crear migración para 9 columnas faltantes
   - Aplicar y validar en desarrollo
   - Ejecutar tests de integración

**2. Corto Plazo** (Este mes):
   - Auditoría manual de 163 columnas obsoletas
   - Decisión caso por caso
   - Migración de limpieza (si aplicable)

**3. Largo Plazo** (v3.0):
   - Diseñar normalización de AgentConfig
   - Migración a estructura multi-tabla
   - Tests exhaustivos de regresión

---

## 📁 ARCHIVOS GENERADOS

1. `audit/inventory_353_columns.csv` - Inventario completo
2. `audit/schema_to_model_mapping.json` - Mapeo Schema-DB
3. `audit/columns_classified.json` - Clasificación de columnas

---

**Auditor**: Sistema Automatizado (Fases 1-3)  
**Certificación**: ⚠️ **CONDICIONADA** a resolución de columnas faltantes  
**Próximos Pasos**: Fase 4-6 (Simulaciones, Matriz completa, Migraciones)
