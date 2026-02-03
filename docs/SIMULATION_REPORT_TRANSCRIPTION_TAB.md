# Reporte de Simulación: Controles de Pestaña Transcriptor (STT Tab)

**Fecha:** 03 de Febrero, 2026
**Objetivo:** Verificar la persistencia y funcionalidad de los controles de la pestaña "Transcriptor" (Speech-to-Text).

## 1. Metodología
Script: `tests/manual/verify_transcription_controls.py`
Proceso: Inyección de actualizaciones JSON para configuración de backend STT.

## 2. Resultados de Controles

| Control | Cambio Simulado | Guardado (DB) | Verificado (API) | Estado | Notas |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **STT Provider** | `deepgram` | ✅ SÍ | ✅ SÍ | ✅ OK | Cambio de proveedor (default: azure) exitoso. |
| **STT Language** | `en-US` | ✅ SÍ | ✅ SÍ | ✅ OK | Cambio de locale correcto. |
| **STT Model** | `nova-2-meeting` | ✅ SÍ | ✅ SÍ | ✅ OK | Modelo específico de Deepgram persistido. |
| **Keywords** | `['Ubrokers', ...]` | ✅ SÍ | ✅ SÍ | ✅ OK | Array JSON guardado correctamente. |
| **VAD Silence** | `750` | ✅ SÍ | ✅ SÍ | ✅ OK | Timeout de silencio (int) actualizado. |
| **Formatting** | `False` | ✅ SÍ | ✅ SÍ | ✅ OK | Flags booleanos funcionales. |
| **Diarization** | `True` | ✅ SÍ | ✅ SÍ | ✅ OK | Feature flag persistido. |

## 3. Conclusiones
La API de configuración maneja correctamente tipos de datos complejos (JSON Arrays para keywords) y booleanos para configuraciones STT. No se detectaron errores de esquema ni de validación.
La migración previa (`fix_schema_drift`) cubrió correctamente estas columnas.
