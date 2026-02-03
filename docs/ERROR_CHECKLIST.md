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

*   [ ] **Validación de Tipos Pydantic**:
    *   **Síntoma**: Error 422 en llamadas API.
    *   **Verificación**: Revisar si un campo numérico está recibiendo un string numérico desde el FormData.
    *   **Solución**: Conversión explícita en el endpoint o validador `BeforeValidator` en Pydantic.

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
