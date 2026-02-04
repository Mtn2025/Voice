# Inventario de Layout: Dashboard

Este documento describe la estructura actual del archivo `app/templates/dashboard.html` y sus componentes principales.

## Estructura General

El layout utiliza **Tailwind CSS** y **Alpine.js** para la interactividad. La estructura se basa en un contenedor flexible (`flex h-screen`) dividido en tres áreas principales:

### 1. Barra de Navegación (Sidebar Rail)
*   **Contenedor**: `<nav class="w-16 flex-none ...">`
*   **Ancho**: Fijo (64px / `w-16`).
*   **Elementos**:
    *   **Logo**: Icono "IA" en gradiente azul.
    *   **Pestañas (Tabs)**: Lista iterada con `x-for`.
        *   Model (`cpu`)
        *   Voz (`mic`)
        *   Oído (`ear`)
        *   Herramientas (`briefcase`)
        *   Campañas (`megaphone`)
        *   Conectividad (`zap`) - *Nota: A veces oculta según lógica*
        *   Sistema (`shield`)
        *   Avanzado (`settings`)
        *   Historial (`history`)
    *   **Tooltips**: Aparecen al hacer hover sobre los iconos.

### 2. Panel de Configuración (Sidebar Config)
*   **Contenedor**: `<aside class="flex-none flex flex-col ...">`
*   **Ancho**: Dinámico/Redimensionable (Default: 480px). Persistido en `localStorage` (`sidebarWidth`).
*   **Header**:
    *   Título "Configuración".
    *   **Selector de Perfil**: Botones para `browser` (Simulador), `twilio`, `telnyx`.
*   **Cuerpo (Formulario)**:
    *   Envuelto en `<form id="configForm">`.
    *   **Área de Scroll**: Contiene los `partial` de cada pestaña.
        *   `partials/tab_model.html`
        *   `partials/tab_voice.html`
        *   `partials/tab_transcriber.html`
        *   ... (resto de tabs)
    *   **Inputs Ocultos**: Gran cantidad de `<input type="hidden">` para vincular los valores de Alpine.js (`configs.*`) al formulario HTML estándar para envío.
*   **Footer**:
    *   Botón "Guardar Configuración" (Sticky bottom).

### 3. Área Principal (Main Content - Simulator)
*   **Contenedor**: `<main class="flex-1 ...">`
*   **Header**:
    *   Título "Simulador de Conversación".
    *   Indicador de estado "Sistema en línea".
*   **Contenido Central**:
    *   Incluye `partials/panel_simulator.html`.
    *   Fondo decorativo (SVG CPU).

## Dependencias de Archivos

| Componente | Archivo Fuente | Descripción |
| :--- | :--- | :--- |
| **JavaScript Core** | `static/js/main.js` | Punto de entrada JS (módulos). |
| **Store** | `static/js/dashboard/store.v2.js` | Lógica de estado (Alpine Store). |
| **Estilos** | `CDN Tailwind` | Configurado en `<head>`. |
| **Iconos** | `partials/icons.html` | Definiciones SVG (Sprites). |
