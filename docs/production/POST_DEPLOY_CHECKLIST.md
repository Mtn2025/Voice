# ✅ Post-Deploy Checklist

Usa estas listas de verificación en orden cronológico tras completar un despliegue.

## ⏱️ Fase 1: Inmediata (0-15 Minutos)
*Objetivo: Confirmar que el servicio está vivo.*

- [ ] **Docker Status:** Todos los contenedores (`app`, `db`) están en estado `Up` o `Healthy`.
- [ ] **Logs de Arranque:** No hay errores fatales (`CRITICAL`, `Panic`) en los logs de inicio de `app`.
- [ ] **Endpoint Health:** `GET /health` devuelve `200 OK`.
- [ ] **Conexión DB:** La aplicación puede consultar la base de datos (verifica logs de migraciones o `/health` si incluye check de DB).
- [ ] **Carga de Env Vars:** Confirmar que claves críticas (API Keys) no están vacías/nulas.

## 🕑 Fase 2: Funcional (15 Minutos - 2 Horas)
*Objetivo: Confirmar que las features principales funcionan.*

- [ ] **Dashboard UI:**
    - [ ] Carga la página principal.
    - [ ] Permite navegar entre pestañas (Simulador, Historial, Configuración).
- **Simulador:**
    - [ ] Inicia sesión de WebSocket.
    - [ ] TTS reproduce audio de bienvenida.
    - [ ] STT transcribe audio del micrófono.
    - [ ] LLM responde coherentemente.
- **Persistencia:**
    - [ ] La llamada simulada aparece en el **Historial**.
    - [ ] Los detalles de la llamada (transcripción) se guardaron.
- **Configuración:**
    - [ ] Modificar un valor (ej. `system_prompt`) y guardar.
    - [ ] Recargar página y verificar que el cambio persiste.

## 📅 Fase 3: Producción Real (Primer Día)
*Objetivo: Validar integración con mundo real.*

- [ ] **Tráfico Telefónico:**
    - [ ] Llamada entrante/saliente vía **Twilio** conecta y fluye audio.
    - [ ] Llamada entrante/saliente vía **Telnyx** conecta y fluye audio.
- **Webhooks:**
    - [ ] Eventos de colgado (`hangup`, `completed`) se reciben y procesan.
- **Extracción de Datos:**
    - [ ] El sistema extrae JSON correcto al finalizar llamadas reales.
    - [ ] Verificar calidad de extracción (precisión > 90%).
- **Estabilidad:**
    - [ ] Monitorear uso de memoria/CPU durante picos de llamadas.

## 🔁 Fase 4: Monitoreo Continuo (Semanal)
*Objetivo: Mantenimiento preventivo.*

- [ ] **Revisión de Logs:** Buscar patrones de errores repetitivos (ej. `429 Too Many Requests` de APIs externas).
- [ ] **Costos API:** Verificar consumo de Groq/Azure/Telephony vs presupuesto.
- [ ] **Backups:** Confirmar que los backups automáticos (si se configuraron) se están generando y no están vacíos.
- [ ] **Latencia:** Verificar que el promedio de respuesta del bot se mantiene bajo (ideal < 800ms).
