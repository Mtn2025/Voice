# 📊 Project Executive Summary: Asistente Andrea

**Versión:** 1.0.0 (Evaluación Producción)
**Fecha:** 2 Febrero 2026

## 1. Idea Original & Propósito

**El Problema:**
La prospección telefónica manual es costosa y escalable solo agregando personal humano. Las soluciones actuales de "Voice AI" (VAPI, BlandAI) son caras (~$0.10/min) y cajas negras difíciles de personalizar para el mercado mexicano.

**La Solución ("Asistente Andrea"):**
Un **orquestador de voz in-house** diseñado específicamente para realizar llamadas en frío (outbound) a bases de datos públicas en México, ofreciendo asesoría fiscal gratuita como gancho ("Lead Magnet") para agendar citas.

**Propuesta de Valor:**
1.  **Costo Controlado:** Elimina intermediarios de orquestación, pagando solo por consumo base (STT/TTS/LLM/Telephony).
2.  **Latencia Baja:** Arquitectura optimizada para conversación fluida.
3.  **Tropicalización:** Prompting y voces ajustadas al español de México.
4.  **Manejo de Escenarios:**
    *   ✅ **Interés:** Agenda cita (Integración futura CRM).
    *   ⏳ **Rechazo Temporal:** Reprograma automáticamente.
    *   ❌ **No Interesa/Inválido:** Limpieza de base de datos.
    *   🛑 **Buzón de Voz:** Detección y corte inteligente (AMD).

## 2. Arquitectura Implementada

El sistema sigue una arquitectura hexagonal (Ports & Adapters) para desacoplar la lógica de negocio de los proveedores externos.

### Diagrama de Alto Nivel
```
[PSTN] <-> [Twilio/Telnyx] <-> [WebSockets API] <-> [Orchestrator Core] <-> [LLM / Audio Services]
                                      ^
                                      |
                                [PostgreSQL]
                                      ^
                                      |
                                [Dashboard Web]
```

### Componentes Clave
1.  **API Gateway (FastAPI):** Rutas separadas para `simulator`, `telephony` (Twilio/Telnyx) y `admin`.
2.  **Orquestador V2:** Núcleo de la lógica de conversación. Gestiona el "Turno de Conversación", interrupciones (Barge-In) y estado.
3.  **Adaptadores de Audio:**
    *   `AzureSpeechAdapter`: TTS y STT de alta calidad.
    *   `TwilioTransport` / `TelnyxTransport`: Normalización de protocolos de WebSocket.
4.  **Servicios de Soporte:**
    *   `ExtractionService`: Analiza la transcripción post-llamada para extraer JSON estructurado (Intención, Resumen, Chequeo de Éxito).
    *   `DatabaseService`: Persistencia asíncrona de historiales.

## 3. Estado Actual del Sistema

El proyecto ha alcanzado una madurez de **"Production-Ready"**.

### Funcionalidades Completas
*   ✅ **Llamadas Reales:** Integración bidireccional de audio probada.
*   ✅ **Dashboard de Control:** Gestión de 9 aspectos de configuración (Prompt, Voz, Reglas de Flujo).
*   ✅ **Simulador Integrado:** Pruebas "End-to-End" sin costo telefónico.
*   ✅ **Observabilidad:** Logs detallados y almacenamiento de audio/transcripciones.
*   ✅ **Resiliencia:** Manejo de reconexiones y errores de API.

### Métricas de Calidad
*   **Cobertura de Tests:** Alta (Suite e2e y unitaria).
*   **Auditoría de Código:** 100/100 Purity Score (Refactorización reciente "Ports & Adapters").
*   **Salud del Dashboard:** 100% Controles conectados (tras corrección de huérfanos).

## 4. Decisiones Técnicas Clave

*   **Docker Compose + Coolify:** Simplifica el despliegue "On-Premise" (VPS propio) para mantener la soberanía de datos y reducir costos de nube.
*   **Groq (Llama 3):** Elegido por su velocidad de inferencia superior, crítica para evitar "silencios incómodos" en llamadas de voz.
*   **Alpine.js:** Framework ligero para el dashboard, eliminando la complejidad de un build step de React/Vue para una app administrativa.

## 5. Próximos Pasos Recomendados

1.  **Escalabilidad:** Realizar pruebas de carga con >50 llamadas simultáneas para afinar el `Concurrency Limit`.
2.  **Integración CRM:** Conectar el `ExtractionService` directamente a un CRM (HubSpot/Salesforce) mediante Webhooks salientes.
3.  **Monitoreo:** Implementar alertas automáticas (Slack/Email) si la tasa de error supera el 5%.

---
**Conclusión:** "Asistente Andrea" es una plataforma robusta y flexible, lista para iniciar campañas de marcado en producción.
