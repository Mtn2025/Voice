# Inventario de Herramientas de Transcripción (STT & VAD)
*Auditoría realizada el 2026-01-26*

Este inventario detalla los controles disponibles en la pestaña `Oído` (`tab_transcriber.html`).

## 1. Speech-to-Text (STT)
- **Proveedor**: `Azure` (Predeterminado).
- **Idioma**: Hereda o sobreescribe la configuración global.

## 2. Control de Turnos (Interrupción)
- **Umbral de Palabras**:
    - Slider: 0 a 10 palabras.
    - Define cuántas palabras debe hablar el usuario antes de interrumpir al bot.
- **Sensibilidad de Voz (RMS)**:
    - Slider: 0 a 1000.
    - Nivel mínimo de energía para considerar audio como "voz" (Pre-filtro).

## 3. Inteligencia de Voz (VAD)
Nueva implementación para detectar silencio y habla humana.
- **Interrupción Inteligente**:
    - Toggle: Activa/Desactiva estrategia semántica.
- **Sensibilidad VAD (Silero)**:
    - Slider: 0.1 (Muy sensible) a 0.9 (Estricto).
    - Controla el umbral del modelo Silero ONNX.
- **Filtros Adicionales** (Telnyx Only):
    - `Krisp AI`: Supresión de ruido de fondo.
    - `VAD Nativo`: Uso del detector de actividad de voz de la telefónica.

## 4. Anti-Alucinaciones
- **Blacklist**: Input de texto para frases prohibidas (ej: "Gracias por llamar" repetido).

## 5. Estado de Implementación
- **Frontend**: Completo (`tab_transcriber.html`).
- **Backend**:
    - VAD: `app/core/vad/analyzer.py` (Silero).
    - STT: `app/services/azure_speech.py` (Reconocimiento continuo).
