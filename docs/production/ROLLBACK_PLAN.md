# 🔄 Rollback Plan (Plan de Reversión)

Este documento define los criterios y pasos para revertir el sistema a una versión estable anterior en caso de fallos críticos tras un despliegue.

## 🚨 Sección 1: ¿Cuándo hacer Rollback?

Ejecuta este plan **INMEDIATAMENTE** si detectas cualquiera de las siguientes condiciones en los primeros 30 minutos post-deploy:

1.  **Fallo Masivo de Extracción:** >50% de las llamadas terminan sin datos extraídos o con JSON corrupto.
2.  **Latencia Inaceptable:** El tiempo de respuesta (TTFB) del audio supera los 3 segundos consistentemente.
3.  **Crash Loop:** El contenedor `app` se reinicia constantemente (ver logs).
4.  **Pérdida de Conectividad:** Los webhooks de Twilio/Telnyx devuelven 500 o Timeouts.
5.  **Corrupción de Datos:** Las transcripciones aparecen vacías o mezcladas en el historial.

---

## 🔙 Sección 2: Procedimiento en Coolify (Automático)

Coolify mantiene un historial de despliegues que facilita la reversión.

1.  Abre el dashboard de **Coolify**.
2.  Navega a tu servicio **"Asistente Andrea"**.
3.  Ve a la pestaña **"Deployments"** (o History).
4.  Identifica el **último despliegue exitoso** (verde) anterior al actual.
5.  Haz clic en el botón **"Redeploy"** o **"Rollback"** (dependiendo de la versión de UI).
6.  Confirma la acción.
    *   *Coolify bajará la versión actual y levantará la imagen Docker anterior.*

---

## 🛠️ Sección 3: Rollback Manual (Emergencia)

Si Coolify no responde o la reversión falla, usa la línea de comandos en el servidor.

### 1. Revertir Código (Git)
Entra al servidor y navega al directorio del proyecto (si usas volúmenes bind) o localmente para hacer push de reversión.

```bash
# En local
git reset --hard HEAD~1  # O al hash del commit estable
git push -f origin main
# (Esto disparará un nuevo deploy en Coolify con el código viejo)
```

### 2. Restaurar Base de Datos (Si hubo corrupción)
Si aplicaste una migración destructiva, restaura el backup generado por `backup_before_deploy.sh`.

```bash
# Desde el servidor (root del proyecto)
./scripts/rollback_production.sh
```

*Este script automatiza:*
1.  Detener contenedores.
2.  Restaurar el dump SQL más reciente.
3.  Reiniciar servicios.

---

## ✅ Sección 4: Verificación Post-Rollback

Después de revertir, verifica inmediatamente:

1.  **Versión:** El endpoint `/health` o logs deben mostrar la versión anterior.
2.  **Base de Datos:** Verifica que el historial de llamadas carga correctamente.
   ```bash
   # Query rápido check
   docker compose exec db psql -U postgres -d app -c "SELECT count(*) FROM calls;"
   ```
3.  **Funcionalidad Crítica:** Realiza una llamada de prueba (Simulador).

---

## 📝 Log de Incidente
Una vez estabilizado el sistema, documenta:
*   Hora del fallo.
*   Síntomas observados.
*   Acción de rollback tomada.
*   Logs relevantes para análisis post-mortem.
