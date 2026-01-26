# Inventario de Frontend (Dashboard)
*Auditoría realizada el 2026-01-26*

## 1. Estructura Modular (Jinja2)
El dashboard ha sido refactorizado en componentes modulares para mejorar la mantenibilidad.
- **`dashboard.html`**: Layout principal (Shell).

### Partials (Componentes)
Ubicación: `app/templates/partials/`

#### UI Tabs (Pestañas)
- **`tab_model.html`**: Configuración de LLM, Prompt del Sistema y Estilo de Conversación.
- **`tab_voice.html`**: Configuración de TTS (Proveedor, Voz, Estilo, Velocidad, Pitch).
- **`tab_transcriber.html`**: Configuración de STT, Umbrales de Silencio y VAD.
- **`tab_campaigns.html`**: Gestor de campañas Outbound (Subida de CSV).
- **`tab_advanced.html`**: Configuración global (Timeouts), CRM y Webhooks.
- **`tab_history.html`**: Tabla de historial de llamadas con filtros y acciones en lote.
- **`tab_connectivity.html`**: Información de conexión y URLs para Twilio/Telnyx.

#### Paneles Laterales
- **`panel_simulator.html`**: Simulador de voz en navegador con visualizador de audio en tiempo real y transcripción.

#### Lógica (JavaScript)
- **`scripts_core_logic.html`**: Inicialización de Alpine.js, gestión de estado reactivo y persistencia de configuración.
- **`scripts_sim_logic.html`**: Manejo de AudioContext, WebSockets y Visualizador (Canvas).
- **`scripts_helpers.html`**: Funciones utilitarias (global scope) para manejo de tablas/historial.
- **`scripts_debug.html`**: Overlay de depuración (oculto/dev).

## 2. Tecnologías
- **Framework CSS**: TailwindCSS (vía CDN).
- **Framework JS**: Alpine.js (vía CDN).
- **Iconografía**: Emojis nativos y SVGs inline.
- **Visualizador**: HTML5 Canvas API.

## 3. Estado de Partials
Todos los módulos se encuentran activos y correctamente enlazados en `dashboard.html`.
- **Integridad**: Verificada.
- **Sintaxis**: Correcta (Fix aplicado en `scripts_core_logic`).
