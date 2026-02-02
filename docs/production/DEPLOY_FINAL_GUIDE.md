# 🚀 Guía Final de Despliegue (Coolify)

Esta guía detalla el proceso paso a paso para desplegar "Asistente Andrea" en un entorno de producción gestionado por Coolify.

## 📋 Sección 1: Pre-requisitos

Antes de iniciar, asegúrate de tener:

1.  **Instancia de Coolify**: Instalada y accesible.
2.  **Repo de GitHub**: Acceso al repositorio del proyecto.
3.  **Provisión de Docker**: La instancia de Coolify debe tener Docker Engine v20.10+ y Docker Compose v2.0+.
4.  **Servicios Externos**:
    *   Cuenta activa en **Groq** (API Key).
    *   Recurso de **Azure Speech Service** (Key y Region).
    *   Cuentas de **Twilio** y **Telnyx** configuradas.

### Puertos Requeridos
Aunque Coolify gestiona el enrutamiento (Traefik), la aplicación expone internamente:
*   **App (FastAPI):** Puerto `8000`
*   **Base de Datos (PostgreSQL):** Puerto `5432`

---

## 🛠️ Sección 2: Pasos de Despliegue en Coolify

### Paso 1: Conectar Repositorio
1.  En el dashboard de Coolify, ve a **Projects** -> **New Project**.
2.  Selecciona el entorno (Environment) y servidor.
3.  Elige **"Public Repository"** (o Private si tienes token configurado).
4.  URL del repo: `https://github.com/tu-usuario/asistente-andrea` (Reemplazar con real).
5.  Branch: `main`.
6.  Build Pack: Selecciona **Docker Compose**.

### Paso 2: Configurar Variables de Entorno
Ve a la pestaña **Environment Variables** y agrega las siguientes claves. **Copia estos valores de tu `.env` local seguro.**

| Variable | Descripción | Ejemplo / Valor |
| :--- | :--- | :--- |
| `PROJECT_NAME` | Nombre del proyecto | `Asistente Andrea` |
| `API_V1_STR` | Prefijo de API | `/api/v1` |
| `POSTGRES_SERVER` | Host de BD (nombre servicio docker) | `db` |
| `POSTGRES_USER` | Usuario BD | `postgres` |
| `POSTGRES_PASSWORD` | Contraseña BD | `secreto_seguro` |
| `POSTGRES_DB` | Nombre BD | `app` |
| `DATABASE_URL` | String de conexión completo | `postgresql://postgres:secreto_seguro@db:5432/app` |
| `GROQ_API_KEY` | API Key de Groq | `gsk_...` |
| `AZURE_SPEECH_KEY` | Key de Azure | `39d8...` |
| `AZURE_SPEECH_REGION` | Región Azure | `eastus` |
| `TWILIO_ACCOUNT_SID` | SID Twilio | `AC...` |
| `TWILIO_AUTH_TOKEN` | Token Twilio | `...` |
| `TELNYX_API_KEY` | Key Telnyx | `KEY...` |
| `ADMIN_API_KEY` | Key para endpoints admin | `admin-secret-123` |

### Paso 3: Configurar Base de Datos
En tu archivo `docker-compose.yml` del repositorio, asegúrate de que el servicio `db` tenga un volumen persistente. Coolify detectará esto, pero verifica en la configuración de almacenamiento (Storage) que `/var/lib/postgresql/data` esté mapeado a un volumen persistente.

### Paso 4: Despliegue Inicial
1.  Haz clic en **Deploy** en la esquina superior derecha.
2.  Observa los logs de "Build". Coolify clonará, construirá la imagen de Docker, y levantará los contenedores.
3.  Espera a que el estado cambie a **"Running"**.

### Paso 5: Aplicar Migraciones
Una vez que la aplicación esté "Running", la base de datos estará vacía. Debemos crear las tablas.

1.  Abre la **Terminal** (Console) de la aplicación en Coolify (dentro del servicio `app`).
2.  Ejecuta el siguiente comando para aplicar migraciones con Alembic:

```bash
alembic upgrade head
```

*Deberías ver una salida indicando que las revisiones se aplicaron (e.g., `Running upgrade -> d1e2f3a4b5c6`).*

### Paso 6: Verificar Health Check
En tu navegador, visita la URL pública que Coolify asignó (o la que configuraste en "Domains").

*   Prueba: `https://tu-dominio.com/health`
*   Respuesta Esperada: `{"status": "ok"}` o similar.
*   Prueba Dashboard: `https://tu-dominio.com/dashboard` (Debería cargar la UI).

---

## ✅ Sección 3: Verificación Post-Deploy

Ejecuta estas pruebas rápidas para confirmar operatividad:

### 1. Verificar Endpoints (Curl)
```bash
# Health
curl -I https://tu-dominio.com/health

# Configuración (Requiere API Key si está protegida)
curl -H "x-api-key: admin-secret-123" https://tu-dominio.com/admin/config
```

### 2. Prueba de Simulador
1.  Ve al **Dashboard** -> Pestaña **Simulador**.
2.  Haz clic en **"Simular Llamada"**.
3.  Habla por el micrófono.
4.  **Validación:** El sistema debe responderte (audio) y transcribir texto en tiempo real.

### 3. Prueba de Extracción y Historial
1.  Termina la llamada simulada.
2.  Ve a la pestaña **Historial**.
3.  **Validación:** La llamada reciente debe aparecer en la tabla.
4.  Haz clic en "Ver Detalles".
5.  **Validación:** Debes ver la transcripción completa y el JSON de extracción (si la "Rubrica de Éxito" estaba configurada).

---

## 🔧 Sección 4: Troubleshooting Común

| Síntoma | Causa Probable | Solución |
| :--- | :--- | :--- |
| **Error 500 / BD Connection Refused** | `DATABASE_URL` incorrecta o DB no lista. | Verifica credenciales en Env Vars. Revisa logs del contenedor `db`. |
| **El asistente no responde (Silencio)** | API Keys de Groq/Azure inválidas. | Revisa logs de `app`. Busca errores `401 Unauthorized`. |
| **Webhooks de Twilio no llegan** | URL pública incorrecta. | Asegúrate de configurar la URL de Coolify en la consola de Twilio (`/api/v1/twilio/webhook`). |
| **CORS Error en Dashboard** | Dominio no en whitelist. | Agrega tu dominio a `BACKEND_CORS_ORIGINS` (formato JSON list o CSV según implementación). |
