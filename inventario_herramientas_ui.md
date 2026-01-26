# Inventario de Herramientas UI (General)
*Auditoría realizada el 2026-01-26*

## 1. Componentes Globales
Elementos disponibles en todo el dashboard.

- **Selector de Perfil**:
    - `Browser (🌐)`: Configuración para pruebas locales.
    - `Twilio (📱)`: Configuración específica para números Twilio.
    - `Telnyx (📡)`: Configuración específica para números Telnyx.
- **Barra de Navegación (Tabs)**:
    - `Modelo`
    - `Voz`
    - `Oído` (Transcriptor)
    - `Campañas` (Nuevo)
    - `Avanzado`
    - `Historial`
    - `Conexión`
- **Botón de Guardado**: Flotante/Fijo en la parte inferior, guarda JSON al endpoint `/api/config/update-json`.

## 2. Simulador (Panel Derecho)
Herramienta de pruebas integrada.

- **Conexión**:
    - Botón `Iniciar Prueba`: Conecta al WebSocket `/ws/media-stream?client=browser`.
    - Indicador de Estado: `Ready` / `Connecting` / `Connected`.
- **Audio**:
    - Visualizador: Canvas HTML5 con 3 modos (Onda, Barras, Orbe).
    - Entrada: Micrófono del navegador (AudioContext @ 16kHz).
    - Salida: Altavoces del navegador.
- **Transcripción**:
    - Chat en vivo: Muestra mensajes `User` (azul) y `Assistant` (verde).
    - Auto-scroll: Activo.

## 3. Feedback Visual
- **Toasts**: Notificaciones flotantes (esquina superior derecha) para éxito/error al guardar.
- **Alertas**: Validaciones de formulario (HTML5 required).
