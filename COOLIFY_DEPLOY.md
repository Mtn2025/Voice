
# Guía de Despliegue en Coolify (Docker) 🐳

Este proyecto está **Dockerizado** y optimizado para desplegarse en [Coolify](https://coolify.io/) u cualquier orquestador de contenedores.

## 1. Configuración del Proyecto en Coolify

*   **Build Pack**: `Docker Compose` (Recomendado) o `Dockerfile`.
*   **Docker Compose File**: El repositorio incluye un `docker-compose.yml`. Si usas *Dockerfile direct deployment*, asegúrate de exponer el puerto `8000`.
*   **Start Command**: No es necesario sobreescribir. El `Dockerfile` ya define:
    ```bash
    CMD ["./scripts/startup.sh"]
    ```
    Este script se encarga de:
    1.  Esperar a la Base de Datos (`wait_for_db`).
    2.  Correr migraciones Alembic.
    3.  **Aplicar Parches Manuales** (Fases 7, 8, 9: Baserow, Webhook, VAD).
    4.  Descargar Modelos AI (Silero VAD).
    5.  Iniciar `uvicorn`.

## 2. Variables de Entorno (Environment Variables)

En Coolify, debes configurar las siguientes variables en la sección **Secrets/Env Vars**:

### Base de Datos
Coolify suele inyectar `DATABASE_URL` o variables `POSTGRES_*`. El sistema soporta ambos métodos, pero **prioriza**:
*   `POSTGRES_SERVER`: (Usualmente el nombre del servicio, ej: `db` o `postgresql`).
*   `POSTGRES_USER`: Usuario de la DB.
*   `POSTGRES_PASSWORD`: Contraseña.
*   `POSTGRES_DB`: `voice_db` (o lo que definas).
*   `POSTGRES_PORT`: `5432`.

### Integraciones (API Keys)
Estas son obligatorias para funcionamiento completo:
*   `TELNYX_API_KEY`: `KEY...`
*   `GROQ_API_KEY`: `gsk...`
*   `AZURE_SPEECH_KEY`: `...`
*   `AZURE_SPEECH_REGION`: `eastus` (ejemplo)

### Seguridad
*   `ADMIN_API_KEY`: Contraseña maestra para acceder al Dashboard.

## 3. Persistencia (Volúmenes)

El `Dockerfile` crea un usuario no-root `app` (UID 1000).
Asegúrate de que los volúmenes montados (si usas SQLite o guardas audios) tengan permisos de escritura para UID 1000.
*   Path de App: `/app`

## 4. Solución de Problemas Comunes

**Error: `UndefinedColumnError`**
*   Causa: Los scripts de parcheo no corrieron.
*   Solución: Revisar logs de inicio. El script `startup.sh` imprime `🛠️ Applying manual patches...`. Si fallan, verificar credenciales de DB.

**Error: `Connection Refused` a DB**
*   Causa: `POSTGRES_SERVER` incorrecto.
*   Solución: En Coolify, verifica el nombre del recurso de base de datos interconectado.
