# Informe Profundo para Implementación (Fases Futuras)
*Plan de Escalabilidad y Endurecimiento - 2026-01-26*

Este documento detalla los pasos críticos para llevar el sistema actual (MVP Robusto) a Producción de Alto Rendimiento (Fases 2 y 3).

## 1. Arquitectura de Despliegue (Producción)
Actualmente el sistema corre en Coolify (Docker). Para alta disponibilidad:
- **Balanceo de Carga**: Nginx/Traefik frente a múltiples réplicas de la app FastAPI.
- **Estado Global**: Migrar `active_calls` (memoria local) a **Redis** completo.
    - *Riesgo Actual*: Si un contenedor se reinicia, se pierden los streams activos.
    - *Solución*: Implementar Redis Pub/Sub para control de llamadas distribuidas.

## 2. Optimización de Latencia
- **Edge Deployment**: Mover el orquestador a servidores geográficamente cercanos a la región de telefonía (us-east-1 para Telnyx).
- **WebRTC Nativo**: Considerar migración futura a WebRTC (vía PipeCat o implementación propia) si la latencia PSTN (>500ms) es inaceptable.

## 3. Seguridad y Cumplimiento
- **Gestión de Secretos**: Migrar `.env` a Vault o AWS Secrets Manager.
- **Auditoría de Acceso**: Implementar logs de acceso al dashboard (quién exportó qué campaña).
- **Retención de Datos**: Política automática de borrado de grabaciones/transcripciones tras 30 días (GDPR/Compliance).

## 4. Mejoras Funcionales (Roadmap)
1.  **IVR Visual**: Editor de flujos tipo n8n dentro del dashboard.
2.  **RAG Contextual**: Inyectar base de conocimiento dinámica (docs PDF) en el prompt del sistema antes de cada llamada.
3.  **Análisis de Sentimiento**: Post-procesado de llamadas para clasificar leads (Interesado/Molesto/Buzón).

## 5. Próximos Pasos Inmediatos
1.  Activar **Redis** en producción.
2.  Configurar **Alertas de Monitoreo** (Prometheus/Grafana) para errores 500 y latencia alta.
3.  Realizar pruebas de carga (100 llamadas simultáneas).
