
# Auditoría de Cambios y Limpieza (Enero 2026)

## 1. Evolución del Proyecto (Fases Recientes)

El sistema ha evolucionado de un asistente de voz básico a una **Plataforma Orquestadora** integrada.

### ✅ Nuevas Integraciones (Core)
| Módulo | Estado | Descripción |
| :--- | :--- | :--- |
| **Baserow CRM** | Productivo | Lectura/Escritura bidireccional. Inyección de contexto y tracking de estados. |
| **Integración Webhook** | Productivo | Reportes tipo "Vapi" al finalizar llamadas (payload JSON completo a n8n). |
| **Motor VAD Híbrido** | Productivo | Silero VAD (On-Device) + Semantic VAD (LLM Check) para interrupciones naturales. |
| **Campañas Outbound** | Productivo | Subida de CSV y discado masivo desde Dashboard. |

### ✅ Blindaje (Robustez)
- **Validación de Prompts**: El sistema impide guardar prompts con variables alucinadas.
- **Validación CSV**: El frontend bloquea archivos malformados.
- **Startup Script**: Auto-reparación de esquema de base de datos al desplegar.

## 2. Limpieza de Archivos ("De-cluttering")

Se han eliminado los siguientes archivos por ser redundantes, temporales o "de adorno":

### 🗑️ Eliminados
- `check_frames_fix.py`, `check_groq.py`, `debug_groq_attrs.py`: Scripts de depuración de una sola vez.
- `temp_deps.txt`, `patch_db.sql`: Artefactos temporales de desarrollo.
- `debug_console_script.js`: Helper de navegador obsoleto.
- `migration_add_voice_language.sql`: Reemplazado por migraciones automáticas.

### ⚠️ Conservados (Críticos)
- `scripts/add_*.py`: Scripts de parcheo necesarios para la transición a Coolify (ejecutados por `startup.sh`).
- `scripts/verify_system_status.py`: Herramienta de health-check recomendada para producción.

## 3. Estado del Repositorio
El repositorio `main` contiene **solo código funcional**. No hay "código muerto" conocido en la ruta crítica de ejecución.
