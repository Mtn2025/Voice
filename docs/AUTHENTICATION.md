# Autenticación - Etapa 1 (API Key Simple)

## Descripción

Sistema de autenticación simple para proteger el dashboard y endpoints de configuración durante la fase de desarrollo. Usa API Key vía header HTTP `X-API-Key`.

**⚠️ ETAPA 1 - DESARROLLO:** Esta es una solución temporal. Será reemplazada por sistema completo de usuarios con JWT en ETAPA 2 (antes de producción).

## Configuración

### 1. Generar API Key

```bash
# En tu máquina local
cd "c:\Users\Martin\Desktop\Asistente Andrea"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Output ejemplo:**
```
dFpB8xQz_-KnY4Rt2wVmC7jLhP3sGfXa0eU9qTkN6oI
```

### 2. Configurar en Coolify

1. Ir a Coolify Dashboard
2. Seleccionar tu proyecto "Asistente Andrea"
3. Ir a **Environment Variables**
4. Añadir nueva variable:
   - **Name:** `ADMIN_API_KEY`
   - **Value:** (pegar la key generada arriba)
5. **Restart** el servicio

### 3. Guardar la API Key de forma segura

⚠️ **IMPORTANTE:** Guarda esta key en un gestor de contraseñas. Quien la tenga puede modificar toda la configuración del sistema.

## Uso

### Acceso vía Navegador

1. Navegar a: `https://tu-dominio.com/dashboard`
2. El sistema solicitará la API Key (solo la primera vez)
3. La key se guarda en `localStorage` del navegador

### Acceso vía API/CLI

```bash
# Obtener configuración
curl -H "X-API-Key: TU_API_KEY_AQUI" \
  https://tu-dominio.com/dashboard

# Modificar configuración
curl -X POST \
  -H "X-API-Key: TU_API_KEY_AQUI" \
  -F "system_prompt=Nuevo prompt" \
  -F "temperature=0.7" \
  https://tu-dominio.com/api/config/update
```

## Endpoints Protegidos

Los siguientes endpoints requieren API Key:

- `GET /dashboard` - Dashboard principal
- `POST /api/config/update` - Actualizar configuración completa
- `POST /api/config/patch` - Actualizar configuración parcial (JSON)
- `GET /dashboard/history-rows` - Obtener filas de historial
- `POST /api/history/delete-selected` - Eliminar llamadas seleccionadas
- `POST /api/history/clear` - Borrar todo el historial
- `GET /dashboard/call/{call_id}` - Detalles de llamada específica

## Endpoints Públicos (Sin Auth)

Los siguientes endpoints permanecen públicos para testing:

- `GET /` - Página principal
- `GET /simulator` - Simulador web de voz
- `WS /api/v1/ws/media-stream` - WebSocket para streaming de audio
- `POST /twilio/incoming-call` - Webhook de Twilio
- `POST /telnyx/call-control` - Webhook de Telnyx

## Troubleshooting

### Error: "Missing X-API-Key header"

**Solución:** Asegúrate de incluir el header en tu request:
```bash
-H "X-API-Key: TU_API_KEY_AQUI"
```

### Error: "Invalid API Key"

**Soluciones:**
1. Verificar que la key en Coolify es correcta
2. Verificar que no hay espacios extra al copiar/pegar
3. Regenerar la key si es necesaria

### Error: "Admin API Key not configured"

**Solución:** La variable `ADMIN_API_KEY` no está configurada en Coolify. Añadirla siguiendo los pasos de configuración.

### Borrar API Key guardada del navegador

```javascript
// En la consola del navegador
localStorage.removeItem('admin_api_key');
location.reload();
```

## Limitaciones Conocidas (ETAPA 1)

Esta es una solución temporal con las siguientes limitaciones:

- ❌ Una sola API Key (quien la tenga tiene acceso total)
- ❌ No hay roles ni permisos diferenciados
- ❌ No hay múltiples usuarios
- ❌ No hay logs de auditoría de cambios
- ❌ No hay expiración de la key
- ❌ No hay sistema de suscripciones

## Próximos Pasos (ETAPA 2)

Antes del lanzamiento a producción, se implementará:

- ✅ Sistema completo de usuarios con base de datos
- ✅ Roles: SuperAdmin / Admin / User
- ✅ Suscripciones: Free / Pro / Enterprise
- ✅ Autenticación con JWT tokens
- ✅ Audit logs de todas las acciones
- ✅ Panel de administración de usuarios
- ✅ Rate limiting y protecciones avanzadas

Ver documento: `plan_trabajo_hallazgo1_actualizado.md` para detalles completos.

## Implementación Técnica

### Módulo: `app/core/auth_simple.py`

Contiene:
- `verify_api_key()` - Dependency de FastAPI para validar API Key
- `generate_api_key()` - Función helper para generar keys seguras

### Modificado: `app/core/config.py`

Añadido:
```python
ADMIN_API_KEY: str = ""
```

### Modificado: `app/routers/dashboard.py`

Todos los endpoints de dashboard incluyen:
```python
dependencies=[Depends(verify_api_key)]
```

## Seguridad

### ✅ Buenas Prácticas Implementadas

1. **Comparación segura:** Usa `secrets.compare_digest()` para evitar timing attacks
2. **Logging:** Registra intentos fallidos de autenticación
3. **Variables de entorno:** API Key nunca en código fuente
4. **Headers estándar:** Usa `X-API-Key` (convención estándar)

### ⚠️ Consideraciones

1. **HTTPS obligatorio:** En producción, siempre usar HTTPS
2. **No compartir la key:** Tratarla como password
3. **Rotación:** Cambiar la key periódicamente
4. **Coolify seguro:** Asegurar que el dashboard de Coolify tiene autenticación

## Testing

Ver documento `plan_de_trabajo_fase1.md` sección "Hallazgo #1 - Testing" para comandos de prueba completos.

---

**Última actualización:** 2026-01-06  
**Versión:** Etapa 1 (Desarrollo)  
**Próxima migración:** Etapa 2 (antes de producción pública)
