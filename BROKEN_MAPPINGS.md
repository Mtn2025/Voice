# Broken Mappings & Data Risks

Este archivo detalla las desconexiones críticas entre la Base de Datos, el Backend y la Interfaz de Usuario.

## Riesgos de Integridad

### 1. `extracted_data` (BD) -> ??? (UI)
*   **Problema**: La columna `extracted_data` existe en la tabla `calls`, pero no hay lógica ni en `history_router.py` ni en `partials/history_rows.html` para mostrar estos datos.
*   **Impacto**: Aunque implementemos la lógica de extracción (que falta), el usuario no podrá ver el resultado (Nombre, Email, Intención) en el dashboard sin cambios de UI.
*   **Severidad**: ALTA (Funcionalidad Incompleta).

### 2. `transcripts` (BD) -> ??? (UI)
*   **Problema**: No existe endpoint ni vista para "Ver Detalle de Llamada". Solo se listan las filas de resumen.
*   **Impacto**: El historial es inútil para control de calidad, ya que no se puede leer qué se dijo.
*   **Severidad**: CRÍTICA (Valor de Negocio Nulo).

## Drift de Nombres (Naming Inconsistencies)

### 1. Interruption Settings
*   **Backend**: `interruption_threshold` (BD) -> `interruption_threshold` (Schema).
*   **Frontend**: `this.c.interruptWords` (JS Store).
*   **Riesgo**: Confusión semántica. "Threshold" suena a sensibilidad (float), "Words" suena a contador (int). En el código parece ser un contador de palabras para el browser, pero en Phone/Telnyx hay un `voice_sensitivity` (RMS). La UI mezcla conceptos.

### 2. Sensitivity vs Threshold
*   **Backend**: `voice_sensitivity` (Integer), `vad_threshold` (Float).
*   **Frontend**: `interruptRMS` (JS Store).
*   **Riesgo**: Si se cambia la escala en Back (e.g. de 0-3000 a 0.0-1.0), el Frontend enviará valores inválidos.

## Validaciones Faltantes
*   No hay validación en tiempo de ejecución de que los objetos JSON de `agent_config` enviados por el Frontend coincidan con los tipos esperados en BD (salvo Pydantic, que devuelve 422, pero la UI no maneja errores de validación granulares, solo muestra "Error al guardar").
