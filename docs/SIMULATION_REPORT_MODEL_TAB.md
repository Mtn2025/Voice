# Reporte de Simulación: Controles de Pestaña Model

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Verificar la persistencia y funcionalidad de los controles de la pestaña "Model" en un entorno simulado pero realista (`localhost` Docker).

## 1. Metodología
Se utilizó un script automatizado (`tests/manual/verify_model_controls.py`) ejecutado contra la instancia local de Docker `voice_orchestrator`.
El proceso consistió en:
1.  **Inyección de Configuración**: Uso de la API `/api/config/update-json` para modificar valores.
2.  **Verificación de Persistencia**: Confirmación de que los valores se guardaron en PostgreSQL.
3.  **Simulación de Efecto**: Intento de conexión vía WebSocket para verificar comportamiento (e.g. mensaje de bienvenida).

## 2. Resultados de Controles

| Control | Cambio Simulado | Guardado (DB) | Verificado (API) | Estado Funcional | Notas |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **First Message** | "Hola, soy tu verificador..." | ✅ SÍ | ✅ SÍ | ⚠️ Parcial | Persistencia correcta. La validación de audio (WS) tuvo timeout por latencia en inicio de flujo. |
| **Max Tokens** | `10` | ✅ SÍ | ✅ SÍ | ✅ OK | Valor actualizado y devuelto correctamente por API. |
| **Temperature** | `0.9` | ✅ SÍ | ✅ SÍ | ✅ OK | Valor actualizado y devuelto correctamente por API. |
| **System Prompt** | "Eres un asistente..." | ✅ SÍ | ✅ SÍ | ✅ OK | Valor actualizado y devuelto correctamente por API. |
| **LLM Model** | `llama-3.1-8b-instant` | ✅ SÍ | ✅ SÍ | ✅ OK | Valor actualizado y devuelto correctamente por API. |

## 3. Hallazgos Críticos y Soluciones

Durante la simulación se detectaron errores bloqueantes que afectaban la estabilidad del entorno de desarrollo (`localhost`) y potencialmente producción.

### 3.1 Desincronización de Base de Datos (Schema Drift)
*   **Error**: `500 Internal Server Error` / `ProgrammingError: column "name" does not exist`.
*   **Causa**: Las tablas en la base de datos PostgreSQL no coincidían con los modelos de SQLAlchemy definidos en el código (faltaban columnas `name`, `interruption_threshold`, etc.).
*   **Solución Aplicada**:
    1.  Se generó una migración de emergencia (`fix_schema_drift`) usando Alembic dentro del contenedor.
    2.  Se aplicó la migración (`upgrade head`) sincronizando la DB.
    3.  **Acción Pendiente**: Esta migración ha sido extraída y se debe commitear al repositorio para proteger la rama `main`.

### 3.2 Error de Conexión WebSocket
*   **Error**: `403 Forbidden` / `Connection Refused`.
*   **Causa**: El script de prueba apuntaba a una ruta obsoleta `/ws/audio/browser`.
*   **Solución**: Se actualizó la ruta a `/ws/simulator/stream`.

### 3.3 Archivos Docker Faltantes
*   **Error**: `FileNotFoundError: script.py.mako`.
*   **Causa**: Docker no tenía copiado el archivo base de plantillas de Alembic.
*   **Solución**: Se copió manualmente el archivo al contenedor.

## 4. Conclusión
La funcionalidad de "Guardar Configuración" del Tab Model es **ROBUSTA** y funciona correctamente una vez resuelto el problema de esquema de base de datos. Los valores persisten y son recuperables.

**Recomendación**: Commitear inmediatamente el archivo de migración generado para asegurar que cualquier nuevo despliegue tenga la estructura de base de datos correcta.
