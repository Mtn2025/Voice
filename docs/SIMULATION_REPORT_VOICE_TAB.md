# Reporte de Simulación: Controles de Pestaña Voz (Voice Tab)

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Verificar la persistencia y funcionalidad de los controles de la pestaña "Voz" tras la corrección de esquemas de base de datos.

## 1. Metodología
Script: `tests/manual/verify_voice_controls.py` (Ejecución local contra Docker)
Proceso: Inyección de JSON vía `/api/config/update-json` -> Verificación de respuesta y persistencia en DB.

## 2. Resultados de Controles

| Control | Cambio Simulado | Guardado (DB) | Verificado (API) | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TTS Provider** | `azure` | ✅ SÍ | ✅ SÍ | ✅ OK | Cambio de proveedor correcto. |
| **Voice Name** | `es-MX-DaliaNeural` | ✅ SÍ | ✅ SÍ | ✅ OK | ID de voz aceptado y persistido. |
| **Voice Style** | `cheerful` | ✅ SÍ | ✅ SÍ | ✅ OK | Columna `voice_style` operativa. |
| **Voice Speed** | `1.2` | ✅ SÍ | ✅ SÍ | ✅ OK | Valor numérico (float) persistido. |
| **Voice Pitch** | `+5` | ✅ SÍ | ✅ SÍ | ✅ OK | Ajuste de tono persistido. |
| **Style Degree** | `1.5` | ✅ SÍ | ✅ SÍ | ✅ OK | Intensidad de estilo persistida. |

## 3. Conclusiones
La corrección del esquema de base de datos (`fix_schema_drift`) ha sido efectiva para todos los campos de configuración de voz. No se requieren parches adicionales.
El sistema acepta y retiene correctamente configuraciones avanzadas de Azure TTS.
