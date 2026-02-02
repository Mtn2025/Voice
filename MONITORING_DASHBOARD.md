# Monitoring Dashboard & Metrics

Métricas claves a vigilar en tiempo real durante la prueba de 3 llamadas.

## 🖥️ Live Viewer (Dashboard)

### 1. Panel de Conexión (WebSocket Status)
*   **Esperado**: `Active Sessions: 1` (Durante la prueba)
*   **Alerta Roja**: `Active Sessions` > 1 (¡Estás llamando a más gente de la debida!) o 0 (Caída de servicio).

### 2. Latencia (TTFB Tracker)
*   **TTS Latency**: < 1200ms (Aceptable), < 800ms (Óptimo).
*   **LLM Latency**: < 1500ms.
*   **Acción**: Si TTS > 3000ms constante, el sistema es inusable -> `ABORT`.

### 3. VAD (Voice Activity Detection)
*   Observar logs en tiempo real.
*   **User Speaking**: Debe cambiar a `TRUE` inmediatamente al hablar.
*   **Interruption**: Si el usuario habla, el bot debe callar en < 500ms.

---

## 📊 Post-Call Verification (SQL / Logs)

### Query de Validación Rápida
Ejecutar después de cada llamada:
```sql
SELECT id, session_id, status, client_type, extracted_data
FROM calls
ORDER BY start_time DESC
LIMIT 1;
```

### Matriz de Salud de Extracción
| Indicador | Estado Saludable | Estado Crítico (STOP) |
| :--- | :--- | :--- |
| **Call Duration** | > 15s (Diálogo real) | < 3s (Crash inmediato) |
| **Extracted Intent** | No nulo (`schedule`, `info`, etc) | `NULL` o `{}` |
| **Transcript Count** | > 4 turns (Ida y vuelta) | 0 turns (Audio unidireccional) |

---

## 🚨 Automated Alerts (Log Patterns)
Vigilar consola por estos strings:
*   `CRITICAL ERROR`: Fallo de sistema.
*   `RateLimitExceeded`: Bloqueo de proveedor.
*   `Hallucination Detected`: El modelo está inventando texto.
