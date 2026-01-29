# 🧪 Mock Testing Environment - Quick Start

## 📋 Descripción

Entorno de simulación completo para testing de barge-in y latencia **sin llamadas telefónicas reales**.

## 🎯 Componentes

### 1. MockTelephonyAdapter
Simula conexión WebSocket/Twilio:
- ✅ Latencia de red configurable
- ✅ Transmisión de audio bidireccional
- ✅ Lifecycle (connect/disconnect)
- ✅ Estadísticas de transmisión

### 2. MockUserAdapter
Simula comportamiento del usuario:
- ✅ Inyección de speech events
- ✅ Interrupciones (barge-in)
- ✅ Scripts de conversación
- ✅ Timestamps precisos

### 3. run_simulation.py
Script de ejecución con escenario de prueba:
- ✅ FSM integration completo
- ✅ Control channel para interrupciones
- ✅ Logs con timestamps en milisegundos
- ✅ Validación automática (PASS/FAIL)

## 🚀 Ejecutar Simulación

```bash
# Desde el directorio del proyecto
python run_simulation.py
```

## 📊 Escenario de Prueba

```
t=0ms      → Sistema inicia (IDLE)
t=100ms    → Usuario dice "Hola"
t=400ms    → Sistema procesa (PROCESSING)
t=400ms    → Sistema empieza a hablar (SPEAKING)
t=900ms    → Usuario interrumpe "Espera, una duda"
t=900ms+   → Sistema corta TTS y vuelve a LISTENING
```

### ✅ Criterios de Éxito

1. **Barge-In Latency < 100ms**
   - Tiempo desde interrupción hasta stop de TTS

2. **FSM Final State = LISTENING**
   - Sistema debe estar listo para nueva entrada

3. **No Crashes**
   - Todas las transiciones válidas

## 📈 Output Esperado

```
================================================================================
🧪 BARGE-IN SIMULATION TEST
================================================================================

Scenario:
  1. User says 'Hola'
  2. System processes (300ms)
  3. System starts speaking
  4. At t=500ms: User interrupts 'Espera, una duda'
  5. System must stop speaking and return to LISTENING

================================================================================

23:45:10.123 | INFO     | 📞 [MockTelephony] Connected (simulated latency: 50ms)
23:45:10.125 | INFO     | 📊 t=    0ms | IDLE         | SYSTEM_INIT     | Orchestrator started
23:45:10.225 | INFO     | 👤 [MockUser] t=100ms | Action 1/2: speak | Data: 'Hola'
23:45:10.275 | INFO     | 📊 t=  152ms | IDLE         | AUDIO_RX        | User spoke: 'Hola'
23:45:10.575 | INFO     | 📊 t=  452ms | SPEAKING     | TTS_START       | Speaking: 'Response to: Hola'
23:45:11.025 | INFO     | 👤 [MockUser] t=900ms | Action 2/2: interrupt | Data: 'Espera, una duda'
23:45:11.075 | INFO     | 📊 t=  952ms | SPEAKING     | INTERRUPT       | User interrupted: 'Espera, una duda'
23:45:11.076 | INFO     | 📊 t=  953ms | SPEAKING     | INTERRUPT_HANDLE| Processing interruption...
23:45:11.078 | INFO     | 📊 t=  955ms | LISTENING    | BARGE_IN_COMPLETE| Latency: 3.2ms

================================================================================
📊 SIMULATION SUMMARY
================================================================================

Total Events: 12
Duration: 1455ms

Event Timeline:
--------------------------------------------------------------------------------
      0ms | IDLE         | SYSTEM_INIT     | Orchestrator started
    152ms | IDLE         | AUDIO_RX        | User spoke: 'Hola'
    452ms | SPEAKING     | TTS_START       | Speaking: 'Response to: Hola'
    952ms | SPEAKING     | INTERRUPT       | User interrupted: 'Espera, una duda'
    953ms | SPEAKING     | INTERRUPT_HANDLE| Processing interruption...
    955ms | LISTENING    | BARGE_IN_COMPLETE| Latency: 3.2ms
   1455ms | LISTENING    | SYSTEM_STOP     | Orchestrator stopped

================================================================================
✅ PASS: Barge-In latency 3.2ms < 100ms
✅ PASS: Final state is LISTENING
================================================================================
```

## 🧪 Pytest Integration

Para tests automatizados:

```bash
# Ejecutar test de barge-in
pytest tests/integration/test_barge_in_simulation.py -v -s
```

## 🛠️ Customización

### Cambiar Escenario

Edita `run_simulation.py`:

```python
# Script custom de conversación
user.script_conversation([
    UserAction(delay_ms=0, action_type="speak", data="Tu mensaje inicial"),
    UserAction(delay_ms=1000, action_type="interrupt", data="Interrupción")
])
```

### Ajustar Latencia

```python
# Mayor latencia de red simulada
orchestrator.telephony = MockTelephonyAdapter(latency_ms=200)
```

### Validaciones Custom

```python
# En SimulationOrchestrator.print_summary()
max_latency = 50  # Más estricto
if latency_ms < max_latency:
    print(f"✅ PASS: Ultra-fast barge-in {latency_ms:.1f}ms")
```

## 📂 Archivos Creados

```
tests/mocks/
├── __init__.py
├── mock_telephony_adapter.py  (Simula WebSocket)
└── mock_user_adapter.py       (Simula usuario)

run_simulation.py              (Script principal)
README_SIMULATION.md           (Esta guía)
```

## 🎯 Próximos Pasos

1. ✅ Ejecutar `python run_simulation.py`
2. ✅ Verificar output (PASS/FAIL)
3. ✅ Ajustar timing si necesario
4. ✅ Integrar en CI/CD (pytest)

## 🐛 Troubleshooting

### ImportError: No module named 'tests'

```bash
# Asegurar que estás en el directorio raíz
cd "c:\Users\Martin\Desktop\Asistente Andrea"
python run_simulation.py
```

### Simulation no interrumpe

Verifica delays en script:
```python
# Debe haber suficiente tiempo para que sistema empiece a hablar
UserAction(delay_ms=800, ...)  # Ajustar según processing time
```

---

**Documentación**: Ver código en `run_simulation.py` para detalles de implementación  
**Soporte**: Revisar logs con timestamps para debug
