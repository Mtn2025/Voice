# Guía de Deployment en Coolify

**Sistema**: Asistente Andrea - Voice Orchestrator  
**Plataforma**: Coolify (Docker Compose)  
**Repositorio**: GitHub auto-deploy

---

## 📋 Variables de Entorno Requeridas

### 1. AI Services (Crítico)

```env
# Azure Speech (STT + TTS)
AZURE_SPEECH_KEY=tu_azure_speech_key_aqui
AZURE_SPEECH_REGION=eastus

# Groq LLM
GROQ_API_KEY=tu_groq_api_key_aqui
GROQ_MODEL=llama-3.3-70b-versatile
```

### 2. Provider Selection (Opcional)

```env
# Defaults: azure (STT/TTS), groq (LLM)
DEFAULT_STT_PROVIDER=azure
DEFAULT_LLM_PROVIDER=groq
DEFAULT_TTS_PROVIDER=azure
```

**Providers Disponibles**:
- STT: `azure`, `google`
- LLM: `groq`, `openai` (production-ready)
- TTS: `azure`, `google`

### 3. Database (Gestionado por Coolify)

```env
POSTGRES_USER=voice_admin
POSTGRES_PASSWORD=<generado-por-coolify>
POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_DB=voice_db
DATABASE_URL=postgresql+asyncpg://...  # Auto-construido
```

⚠️ **Nunca usar passwords por defecto** (`postgres`, `password`) - Pydantic validators rechazan valores inseguros.

### 4. Security

```env
ADMIN_API_KEY=<token-seguro-generado>
DEBUG=false
APP_ENV=production
```

### 5. Telephony (Opcional)

```env
# Telnyx (Production telephony provider)
TELNYX_API_KEY=xxxxx
TELNYX_PUBLIC_KEY=xxxxx
```

---

## 🚀 Proceso de Deployment

### 1. Configurar Proyecto en Coolify

1. **Crear Nuevo Recurso** → Docker Compose
2. **Conectar GitHub Repo**: `https://github.com/tu-org/asistente-andrea`
3. **Branch**: `main` (o `production`)
4. **Build Pack**: Nixpacks o Dockerfile

### 2. Configurar Variables de Entorno

**En Coolify Dashboard**:
1. Environment Variables → Add Variable
2. Copiar todas las vars de sección anterior
3. ✅ Validar que `AZURE_SPEECH_KEY` y `GROQ_API_KEY` estén set

⚠️ **Crítico**: Sistema NO arrancará sin `POSTGRES_USER` y `POSTGRES_PASSWORD` (Pydantic validators).

### 3. Configurar Database

**Opción A: Database Coolify Managed**
1. Resources → New → PostgreSQL
2. Coolify auto-genera `DATABASE_URL`
3. Copiar `DATABASE_URL` a env vars del app

**Opción B: External Database**
```env
DATABASE_URL=postgresql+asyncpg://user:pass@external-host:5432/dbname
```

### 4. Deploy

```bash
# En Coolify: Deploy button
# O git push (auto-deploy configurado):
git push origin main
```

**Coolify ejecuta**:
1. `git pull` desde GitHub
2. `docker-compose build`
3. Inyecta ENV vars
4. `docker-compose up -d`

### 5. Verificar Logs

```bash
# En Coolify Dashboard → Logs
# Buscar:
✅ [VoicePorts] STT configured: azure
✅ [VoicePorts] LLM configured: groq
✅ [VoicePorts] TTS configured: azure
```

⚠️ **Warnings esperados** (no rompen deploy):
```
⚠️ [Config] AZURE_SPEECH_KEY is not set. Service may fail at runtime.
```

Si ves este warning, **agrega la API key inmediatamente**.

---

## 🔍 Troubleshooting

### Error: `ValueError: POSTGRES_USER must be set`

**Causa**: Database credentials vacías  
**Solución**:
```env
POSTGRES_USER=tu_usuario_seguro
POSTGRES_PASSWORD=<minimo-12-caracteres>
```

### Error: `Unknown STT provider: 'deepgram'`

**Causa**: Provider no registrado en registry  
**Solución**: Usar provider disponible
```env
DEFAULT_STT_PROVIDER=azure  # o 'google'
```

### Warning: API Keys Missing

**Síntoma**:
```
⚠️ [Config] GROQ_API_KEY is not set
```

**Impacto**: Primera llamada fallará (no hay fallback para LLM)  
**Solución**: Agregar key en Coolify env vars → Re-deploy

### Fallback Activation

**Log normal** (no es error):
```
⚠️ [STT Azure] Error: 401 Unauthorized
✅ [STT Fallback] Switching to Google STT
```

**Acción**: Verificar `AZURE_SPEECH_KEY` válida

---

## 📊 Monitoreo Post-Deploy

### Métricas Clave (Ver en Logs)

#### 1. Config Warnings
```bash
grep "⚠️ \[Config\]" logs/app.log
```

**Acción**: Si ves warnings, agregar API keys faltantes.

#### 2. Fallback Activation
```bash
grep "Fallback" logs/app.log | wc -l
```

**Normal**: 0-5% de llamadas usan fallback  
**Problema**: >10% indica primary provider fallando

#### 3. TTFB (Time to First Byte)
```bash
grep "TTFB" logs/app.log
```

**Objetivo**:
- TTS: <500ms
- STT: <200ms
- LLM: <1000ms

### Alertas Recomendadas

**Si tienes Prometheus/Grafana**:
```promql
# Config warnings rate
sum(rate(config_warning_total[5m])) by (field_name) > 0

# Fallback activation rate
sum(rate(fallback_activated_total[5m])) by (provider_type) > 0.1

# TTFB degradation
histogram_quantile(0.95, tts_ttfb_seconds) > 1.0
```

**Si solo tienes logs** (Coolify default):
Crear script de alerta:
```bash
#!/bin/bash
# alert_config_warnings.sh
tail -f /var/log/app.log | grep "⚠️ \[Config\]" | \
  while read line; do
    echo "ALERT: $line" | mail -s "Config Warning" ops@yourcompany.com
  done
```

---

## 🔐 Seguridad

### Secrets Management

✅ **Correcto** (Coolify ENV vars):
```env
GROQ_API_KEY=xxxxx  # Encriptado en Coolify
```

❌ **Incorrecto** (hardcoded):
```python
# ❌ NUNCA HACER ESTO
GROQ_API_KEY = "gsk_xxxxx"  # En código
```

### CSRF Protection

```env
ADMIN_API_KEY=<token-aleatorio-seguro>
```

Generar:
```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

---

## 🧪 Testing en Staging

Antes de producción:

1. **Deploy a staging** (Coolify environment separado)
2. **Verificar logs** (sin warnings críticos)
3. **Hacer llamada de prueba**:
   ```bash
   curl -X POST https://staging.tuapp.com/api/v1/voice/call \
     -H "Authorization: Bearer $ADMIN_API_KEY" \
     -d '{"agent_id": 1, "from": "+1234567890"}'
   ```
4. **Revisar métricas** (TTFB, fallback rate)
5. **Si todo OK** → Deploy a producción

---

## 📚 Recursos Adicionales

- [Coolify Documentation](https://coolify.io/docs)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

**Soporte**: Ver `README.md` para contacto del equipo

---

**Última Actualización**: 2026-01-29
