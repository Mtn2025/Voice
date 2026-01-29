# Guía de Monitoreo Post-Deploy

**Sistema**: Asistente Andrea - Voice Orchestrator  
**Tipo**: Monitoreo de Producción  
**Última Actualización**: 2026-01-29

---

## 🎯 Métricas Clave

### 1. Config Warnings (CRÍTICO)

**Síntoma**: API keys faltantes detectadas en startup

**Comando de Búsqueda**:
```bash
# Coolify Logs
grep "⚠️ \[Config\]" /var/log/app.log

# Docker logs
docker logs asistente-andrea 2>&1 | grep "\[Config\]"
```

**Log Esperado**:
```
⚠️ [Config] AZURE_SPEECH_KEY is not set. Service may fail at runtime.
⚠️ [Config] GROQ_API_KEY is not set. Service may fail at runtime.
```

**Acción Inmediata**:
1. Agregar API key faltante en Coolify ENV vars
2. Re-deploy aplicación
3. Verificar warning desaparezca

**Severidad**: 🔴 **CRÍTICA** - Primera llamada fallará

---

### 2. Fallback Activation Rate

**Síntoma**: Primary provider fallando, sistema usa fallback

**Comando de Búsqueda**:
```bash
# Count fallback activations
grep "Fallback" /var/log/app.log | wc -l

# Ver cuál provider está fallando
grep "Switching to" /var/log/app.log
```

**Log Normal**:
```
✅ [STT Azure] Synthesis complete
✅ [LLM Groq] Response generated
✅ [TTS Azure] Audio streamed
```

**Log de Fallback** (no es error):
```
⚠️ [STT Azure] Error: 401 Unauthorized
✅ [STT Fallback] Switching to Google STT
```

**Umbral Saludable**:
- ✅ **0-5%** de llamadas usan fallback (normal)
- ⚠️ **5-10%** investigar API key o quotas
- 🔴 **>10%** problema crítico con primary provider

**Acción**:
```bash
# Verificar API key válida
echo $AZURE_SPEECH_KEY | wc -c  # Debe ser >10 caracteres

# Verificar cuota Azure
# (dashboard Azure Portal → Cognitive Services → Quotas)
```

---

### 3. TTFB (Time to First Byte)

**Objetivo**: Latencia baja para experiencia conversacional fluida

**Comando de Búsqueda**:
```bash
# Extraer métricas TTFB
grep "TTFB" /var/log/app.log | tail -20
```

**Log Esperado**:
```
📊 [TTS Azure] trace=abc123 TTFB=342ms total=1.2s
📊 [STT Azure] trace=abc123 TTFB=156ms
📊 [LLM Groq] trace=abc123 TTFB=723ms chunks=45
```

**Umbrales Objetivo**:
| Provider | Target TTFB | Warning | Critical |
|----------|-------------|---------|----------|
| TTS      | <500ms      | 500-1s  | >1000ms  |
| STT      | <200ms      | 200-500ms | >500ms |
| LLM      | <1000ms     | 1-2s    | >2000ms  |

**Acción si TTFB Alta**:
1. Verificar latencia de red (ping a Azure/Groq endpoints)
2. Revisar CPU/memoria del servidor (Coolify metrics)
3. Considerar cambiar región de Azure (más cercana)

---

### 4. Concurrent Calls

**Objetivo**: Sistema soporta 10-20 llamadas simultáneas

**Comando de Búsqueda**:
```bash
# Contar WebSockets activos
grep "WS CONNECTION" /var/log/app.log | grep -v "closed" | wc -l

# Ver patrón de conexiones
grep "WS CONNECTION\|WS CLOSED" /var/log/app.log | tail -50
```

**Log Saludable**:
```
🔌 WS CONNECTION | Client: twilio, ID: call_123
🔌 WS CONNECTION | Client: telnyx, ID: call_456
...
✅ WS CLOSED | ID: call_123 duration=45s
```

**Umbral**:
- ✅ **0-20 llamadas**: Normal (Factory pattern soporta aislamiento)
- ⚠️ **20-50 llamadas**: Considerar escalar horizontalmente
- 🔴 **>50 llamadas**: Requiere load balancer + multi-instance

---

### 5. Error Rate

**Objetivo**: <1% de llamadas con errores

**Comando de Búsqueda**:
```bash
# Count errors
grep "❌\|ERROR" /var/log/app.log | wc -l

# Ver errores recientes
grep "❌" /var/log/app.log | tail -10
```

**Errores Comunes**:

#### Error: 401 Unauthorized
```
❌ [TTS Azure] Error: 401 Unauthorized
```
**Causa**: API key inválida  
**Solución**: Verificar `AZURE_SPEECH_KEY` en Coolify

#### Error: 429 Too Many Requests
```
❌ [LLM Groq] Error: RateLimitError (429)
```
**Causa**: Quota excedida  
**Solución**: Upgrade plan o implementar rate limiting

#### Error: Connection Timeout
```
❌ [STT Azure] Error: Connection timeout after 30s
```
**Causa**: Latencia de red  
**Solución**: Verificar conectividad, cambiar región

---

## 🚨 Alertas Automatizadas

### Opción A: Log-Based Alerts (Bash Script)

```bash
#!/bin/bash
# /opt/scripts/alert_config_warnings.sh

LOG_FILE="/var/log/app.log"
ALERT_EMAIL="ops@yourcompany.com"

# Monitor config warnings
tail -f $LOG_FILE | grep --line-buffered "⚠️ \[Config\]" | \
while read LINE; do
  echo "ALERT: Missing API Key" | mail -s "[PROD] Config Warning" $ALERT_EMAIL
  echo "$LINE"
done
```

**Ejecutar con systemd**:
```ini
# /etc/systemd/system/voice-alerts.service
[Unit]
Description=Voice Orchestrator Alerts
After=syslog.target

[Service]
Type=simple
ExecStart=/opt/scripts/alert_config_warnings.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

### Opción B: Prometheus + Grafana (Avanzado)

**Si ya tienes Prometheus**:

#### Metrics Exposed
```python
# app/observability/metrics.py (ya existe)
from prometheus_client import Counter, Histogram

config_warnings = Counter(
    'config_warning_total', 
    'Config validation warnings',
    ['field_name']
)

fallback_activations = Counter(
    'fallback_activated_total',
    'Fallback provider activations',
    ['provider_type']
)

ttfb_histogram = Histogram(
    'tts_ttfb_seconds',
    'TTS Time to First Byte',
    ['provider']
)
```

#### Alertas Prometheus
```yaml
# prometheus_alerts.yml
groups:
  - name: voice_orchestrator
    rules:
      # Config warnings (cualquier warning = alerta)
      - alert: ConfigWarningDetected
        expr: increase(config_warning_total[5m]) > 0
        labels:
          severity: critical
        annotations:
          summary: "Missing API key detected"
          description: "Field {{ $labels.field_name }} not configured"
      
      # Fallback rate alta
      - alert: HighFallbackRate
        expr: rate(fallback_activated_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High fallback activation rate"
          description: "{{ $labels.provider_type }} primary failing"
      
      # TTFB degradado
      - alert: HighTTFB
        expr: histogram_quantile(0.95, tts_ttfb_seconds) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "TTS latency degraded"
          description: "95th percentile TTFB > 1s"
```

---

## 📊 Dashboard Recomendado (Grafana)

### Paneles Clave

1. **Config Health**
   - Red/Green indicator: "All API keys configured"
   - Last warning timestamp

2. **Fallback Rate**
   - Line chart: Fallback activations/minute
   - Split by provider (STT, LLM, TTS)

3. **TTFB Latency**
   - Heatmap: P50/P95/P99 TTFB
   - Goal line at 500ms (TTS), 200ms (STT), 1000ms (LLM)

4. **Concurrent Calls**
   - Gauge: Active WebSocket connections
   - Max limit line at 20

5. **Error Rate**
   - Single stat: Errors/minute
   - Goal: <1

---

## 🔍 Troubleshooting Playbook

### Escenario 1: Spike en Fallback Rate

**Síntomas**:
```
✅ [TTS Fallback] Switching to Google TTS (50 times in 1 hour)
```

**Pasos**:
1. Verificar Azure Status Page (outage?)
2. Verificar API key válida
3. Verificar quota no excedida
4. Si persiste, contactar soporte Azure

### Escenario 2: TTFB Súbitamente Alto

**Síntomas**:
```
📊 [TTS Azure] TTFB=3.2s (normal: 300ms)
```

**Pasos**:
1. Ping Azure endpoint:
   ```bash
   ping eastus.tts.speech.microsoft.com
   ```
2. Verificar CPU/Memoria servidor (Coolify metrics)
3. Verificar no hay rate limiting (429 errors)
4. Considerar cambiar región Azure

### Escenario 3: Config Warning en Producción

**Síntomas**:
```
⚠️ [Config] GROQ_API_KEY is not set
```

**Pasos** (URGENTE):
1. Entrar a Coolify Dashboard
2. Environment Variables → Add `GROQ_API_KEY`
3. Click "Deploy" (re-deploy con nueva var)
4. Verificar warning desaparezca en logs

---

## 📧 Notificaciones

### Email Template (Config Warning)

**Subject**: `[PROD] ⚠️ API Key Missing - Voice Orchestrator`

**Body**:
```
Alerta: API Key faltante detectada en producción

Field: GROQ_API_KEY
Timestamp: 2026-01-29 03:00:00
Server: voice-prod-01

Impacto: Primera llamada fallará (sin fallback para LLM)

Acción Requerida:
1. Agregar GROQ_API_KEY en Coolify ENV vars
2. Re-deploy aplicación
3. Verificar warning desaparezca

Dashboard: https://coolify.yourcompany.com/logs
```

---

## 🎯 KPIs Semanales

**Reporte para Ops Team**:

| Métrica | Target | Actual | Estado |
|---------|--------|--------|--------|
| Config Warnings | 0 | 0 | ✅ |
| Fallback Rate | <5% | 2.3% | ✅ |
| TTFB P95 (TTS) | <500ms | 387ms | ✅ |
| Error Rate | <1% | 0.4% | ✅ |
| Uptime | >99% | 99.8% | ✅ |

**Generar reporte**:
```bash
#!/bin/bash
# weekly_report.sh

echo "## Voice Orchestrator - Weekly Report"
echo "Week: $(date +%Y-W%U)"
echo ""

# Config warnings
WARNINGS=$(grep -c "⚠️ \[Config\]" /var/log/app.log.1)
echo "Config Warnings: $WARNINGS"

# Fallback rate
TOTAL_CALLS=$(grep -c "WS CONNECTION" /var/log/app.log.1)
FALLBACKS=$(grep -c "Fallback" /var/log/app.log.1)
FALLBACK_RATE=$(echo "scale=2; $FALLBACKS / $TOTAL_CALLS * 100" | bc)
echo "Fallback Rate: ${FALLBACK_RATE}%"

# TTFB average
AVG_TTFB=$(grep "TTFB" /var/log/app.log.1 | \
  grep -oP 'TTFB=\K\d+' | \
  awk '{sum+=$1; count++} END {print sum/count}')
echo "Avg TTFB: ${AVG_TTFB}ms"
```

---

**Responsable de Monitoreo**: Ops Team  
**Contacto Escalación**: DevOps Lead  
**Horario de Soporte**: 24/7 (producción crítica)
