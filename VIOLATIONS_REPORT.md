# Violations Report: Architectural Separation (Simulator/Twilio/Telnyx)

Este reporte detalla las violaciones al contrato de separación de responsabilidades entre los 3 perfiles.

## Resumen
Se identificaron 0 violaciones CRÍTICAS, 2 de severidad ALTA y 3 de MEDIA.
El sistema **no** está roto, pero presenta acoplamiento que dificulta la escalabilidad y tests aislados.

---

## Violaciones Críticas (0)
*No se encontraron violaciones críticas que rompan el sistema (ej. importar código de Twilio dentro de lógica que corre solo para el Simulador).*

---

## Violaciones de Severidad ALTA (2)
Estas violaciones representan un acoplamiento indebido de lógica de negocio dentro de adaptadores técnicos.

| Archivo | Elemento | Descripción del Problema |
| :--- | :--- | :--- |
| `app/adapters/outbound/tts/azure_tts_adapter.py` | Clase `AzureTTSAdapter` | **Violación de Aislamiento**: El adaptador recibe `audio_mode` ("browser", "telnyx", "twilio") y contiene lógica `if/else` para derivar el formato de audio. <br>**Solución**: El adaptador debe recibir parámetros técnicos (`sample_rate`, `encoding`) inyectados desde el Orchestrator/Config, y ser agnóstico del perfil. |
| `app/adapters/outbound/stt/azure_stt_adapter.py` | Clase `AzureSTTAdapter` | **Violación de Aislamiento**: Similar al TTS, el adaptador STT decide el formato de audio basándose en `config.audio_mode` ("browser" vs otros). <br>**Solución**: Inyectar configuración técnica explícita. |

---

## Violaciones de Severidad MEDIA (3)
Estas violaciones representan deuda técnica o contaminación de capas.

| Archivo | Elemento | Descripción del Problema |
| :--- | :--- | :--- |
| `app/api/routes_v2.py` | Endpoint `/ws/media-stream` | **Contaminación de Lógica**: El handler WebSocket genérico maneja explícitamente el evento `vad` (nativo de Telnyx). Si Twilio envía un evento similar o diferente, el código se volverá un espagueti de `if/else`. <br>**Solución**: Mover el manejo de eventos específicos del protocolo al `TelephonyTransport`. |
| `app/api/routes_v2.py` | Endpoint `/calls/test-outbound` | **Acoplamiento Fuerte**: El endpoint se llama genéricamente "test-outbound" pero su implementación es **100% Telnyx hardcoded**. No soporta Twilio ni Simulador. <br>**Solución**: Renombrar a `/telnyx/test-outbound` o implementar factory para soportar múltiples proveedores. |
| `app/api/routes_v2.py` | Imports | **Mezcla de Dependencias**: El archivo de rutas importa tanto `SimulatorTransport` como `TelephonyTransport`. Aunque funcional, idealmente deberían estar en módulos de router separados (`routes_simulator.py`, `routes_telephony.py`) para evitar cargar dependencias de uno en el otro. |

---

## Próximos Pasos
Se recomienda corregir las violaciones de severidad ALTA refactorizando la inicialización de los adaptadores Azure para aceptar `Authentication`, `AudioFormat` y `LatencyConfig` en lugar de `ProfileName`.
