# Guía de Resolución de Problemas en Producción (Quick Fixes)

Este documento detalla procedimientos de emergencia para resolver errores críticos detectados durante simulaciones y despliegues.

## 1. Desincronización de Base de Datos (Schema Drift)

**Síntoma:** Error 500 en endpoints que tocan la base de datos (ej. guardar configuración).
**Log:** `ProgrammingError: column "name" does not exist` (o similar).
**Causa:** La base de datos real tiene columnas faltantes respecto al código, y Alembic cree erróneamente que está sincronizada.

**Solución Rápida (Sin pérdida de datos):**

1.  **Entrar al contenedor de aplicación:**
    ```bash
    docker compose exec app bash
    ```

2.  **Generar Migración de Ajuste (Auto-detect):**
    ```bash
    alembic revision --autogenerate -m "fix_schema_drift_emergency"
    ```

3.  **Aplicar Migración:**
    ```bash
    alembic upgrade head
    ```

4.  **Verificar:**
    Reintentar la operación que fallaba. Si funciona, **EXTRAER** el archivo generado en `/app/alembic/versions/` y commitearlo al repo inmediatamente.

---

## 2. Archivos Faltantes en Docker (Bind Mounts)

**Síntoma:** `FileNotFoundError: /app/ruta/archivo.py`
**Causa:** El archivo existe en el repo local pero no se copió a la imagen Docker (falta en Dockerfile o `.dockerignore`), o se está usando un volumen que oculta los cambios nuevos.

**Solución Rápida (Inyección):**

1.  **Copiar archivo desde Host al Contenedor:**
    ```powershell
    # Desde el host (Windows/Linux)
    docker cp ruta/local/archivo.py voice_orchestrator:/app/ruta/destino/
    ```

2.  **Reiniciar servicio (si es código Python):**
    ```powershell
    docker compose restart app
    ```

**Solución Permanente:**
*   Agregar el archivo explícitamente al `Dockerfile`.
*   O revisar `docker-compose.yml` para asegurar que el volumen mapeado incluya la carpeta nueva.

---

## 3. Conexión Rechazada (Refused) en Localhost

**Síntoma:** `ConnectionRefusedError` o 403 al conectar a `localhost:8000`.
**Causa:**
1.  El servicio no está corriendo (`docker ps` para verificar).
2.  El puerto no está expuesto en `docker-compose.yml`.

**Solución:**
1.  Editar `docker-compose.yml` y asegurar:
    ```yaml
    ports:
      - "8000:8000"
    ```
2.  Aplicar cambios:
    ```powershell
    docker compose up -d --force-recreate app
    ```
