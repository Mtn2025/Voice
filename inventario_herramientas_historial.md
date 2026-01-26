# Inventario de Historial de Llamadas
*Auditoría realizada el 2026-01-26*

Este inventario detalla los controles disponibles en la pestaña `Historial` (`tab_history.html`).

## 1. Visualización de Datos
- **Tabla Resumen**:
    - Columnas: Checkbox, Fecha/Hora, Fuente (Icono/Badge), Duración, Enlace.
- **Filtros Rápidos**:
    - `Todos`: Muestra todo el historial.
    - `Simulador`: Solo llamadas vía navegador.
    - `Twilio`: Llamadas telefónicas Twilio.
    - `Telnyx`: Llamadas telefónicas Telnyx.

## 2. Acciones
- **Ver Detalle**: Enlace a `/dashboard/call/{id}`.
- **Selección Múltiple**:
    - Checkbox "Select All" en cabecera.
    - Checkbox individual por fila.
- **Borrado Masivo**:
    - Botón `Borrar Seleccionados`: Aparece dinámicamente al seleccionar items.
    - Botón `Borrar Historial Completo`: Limpieza total de la tabla.

## 3. Backend
- **Endpoint**: `GET /api/history/rows` (HTMX).
- **DB Model**: Tabla `calls` en PostgreSQL.
