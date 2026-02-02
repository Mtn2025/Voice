# Production Test Plan: 3-Call Controlled Burst

Este plan define ESTRICTAMENTE las 3 llamadas permitidas para verificar la infraestructura en producción.
**REGLA DE HIERRO**: Si la llamada #1 falla en lógica crítica (extracción/guardado), **NO** realizar la llamada #2.

## 👥 Números de Prueba (Lista Cerrada)
Nunca usar números de prospectos reales para esta fase. usar teléfonos del equipo interno.

1.  **Test Lead A (Happy Path)**: `[INSERT_NUMBER_1]`
2.  **Test Lead B (Rejection)**: `[INSERT_NUMBER_2]`
3.  **Test Lead C (Edge Case)**: `[INSERT_NUMBER_3]` (Opcional: Dejar ir a buzón)

---

## 🧪 Escenarios de Prueba

### Escenario 1: "El Cliente Ideal" (Test Lead A)
*   **Acción Humana**: Contestar "Hola", escuchar greeting, preguntar "¿De qué se trata?", esperar respuesta, decir "Sí me interesa, ¿puedes el martes a las 10?", confirmar, colgar.
*   **Verificación Backend**:
    *   `Call Status`: `completed`
    *   `Extracted Data`:
        *   `intent`: `appointment_scheduling` (o similar)
        *   `date`: Próximo martes 10am (ISO format)
    *   **CRÍTICO**: El historial debe existir en Dashboard y el registro en Baserow debe crearse/actualizarse.

### Escenario 2: "El Rechazo Amable" (Test Lead B)
*   **Acción Humana**: Contestar, escuchar, interrumpir a mitad del pitch: "No me interesa ahora, márcame en dos semanas".
*   **Verificación Backend**:
    *   `Call Status`: `completed`
    *   `Extracted Data`:
        *   `intent`: `callback_requested` / `not_interested_now`
        *   `next_action_date`: +15 días (aprox)
    *   **CRÍTICO**: El sistema debe reconocer la negación y no insistir agresivamente.

### Escenario 3: "La Falla Técnica" (Test Lead C - Opcional)
*   **Acción Humana**: Dejar sonar hasta buzón de voz O contestar y no decir NADA (silencio absoluto).
*   **Verificación Backend**:
    *   **Caso Buzón**: `machine_detection` debe activar `voicemail_message` o colgar.
    *   **Caso Silencio**: `idle_timeout` debe disparar "¿Hola?" x2 y luego colgar.
    *   **Estado Final**: `failed` o `no_answer` o `completed` (si dejó mensaje).

---

## 🛑 Criterios de Parada (Abort Mission)

Ejecutar `emergency_stop.sh` INMEDIATAMENTE si:
1.  El bot entra en loop infinito ("Hola hola hola").
2.  Se detecta latencia > 3 segundos sistemática.
3.  **Extracción Vacía**: Al finalizar la Llamada 1, el JSON de extracción está nulo.
4.  **Pérdida de Datos**: La llamada finaliza pero NO aparece en el Historial del Dashboard.

## Checklist Pre-Vuelo
- [ ] Base de datos limpia (o ids de prueba identificados)
- [ ] Dashboard abierto en `Log Stream`
- [ ] `emergency_stop.sh` con permisos de ejecución (`chmod +x`)
