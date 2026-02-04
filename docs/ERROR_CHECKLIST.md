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

*   [ ] **Desalineación de Payloads Frontend-Backend**:
    *   **Síntoma**: Errores silenciosos donde campos del frontend no se guardan en DB.
    *   **Causa Técnica**: El endpoint `/api/config/update-json` utiliza un mapeo manual (`FIELD_ALIASES`) que puede estar desactualizado respecto al HTML o al Modelo DB.
    *   **Solución Arquitectónica**:
        1.  **Validación Estricta**: Implementar esquemas Pydantic que rechacen keys no mapeadas (hoy se ignoran con warning).
        2.  **Pruebas de Integración**: Scripts que iteren sobre el esquema JSON esperado y validen `updated_count > 0`.
        3.  **Single Source of Truth**: Generar el formulario HTML dinámicamente desde el esquema Pydantic para evitar discrepancias.
