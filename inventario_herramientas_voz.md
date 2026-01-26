# Inventario de Herramientas de Voz (TTS)
*Auditoría realizada el 2026-01-26*

Este inventario detalla los controles disponibles en la pestaña `Voz` (`tab_voice.html`).

## 1. Selección de Motor
- **Proveedor TTS**:
    - `Azure` (Predeterminado).
    - Opción extensible a ElevenLabs/OpenAI (actualmente solo Azure visible).
- **Idioma**:
    - Lista dinámica basada en el proveedor (ej: `es-MX`, `en-US`).
- **Género**:
    - Filtros rápidos: `Femenino`, `Masculino`, `Neutral`.
- **Voz**:
    - Lista desplegable con IDs de modelos (ej: `es-MX-DaliaNeural`).
- **Estilo Emocional**:
    - Selector de estilos Azure (ej: `sad`, `cheerful`, `whispering`).
    - Solo aparece si la voz soporta estilos.

## 2. Ajustes de Audio (Prosodia)
- **Velocidad**:
    - Slider: 0.5x a 2.0x.
- **Tono (Pitch)**:
    - Slider: -12st a +12st (semitonos).
- **Volumen**:
    - Slider: 50% a 100%.
- **Intensidad de Estilo**:
    - Slider: 0.5 a 2.0 (Solo si hay estilo seleccionado).

## 3. Ambiente (Fondo)
- **Sonido de Fondo**:
    - Opciones: `Silencio` (Default), `Oficina`, `Cafetería`, `Call Center`.
    - `URL Personalizada`: Input de texto para stream de audio remoto.

## 4. Estado de Implementación
- **Frontend**: Completo (`tab_voice.html`).
- **Backend**: `app/services/azure_speech.py` implementa SSML dinámico respetando estos parámtros.
