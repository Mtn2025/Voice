# Manejo Seguro de Secretos - Guía Completa

## RESUMEN

Este proyecto implementa múltiples capas de protección para evitar la exposición de API keys, tokens y passwords en logs o repositorio Git.

## ✅ Protecciones Implementadas

### 1. Sistema de Logging Seguro

**Módulo:** `app/core/secure_logging.py`

**Características:**
- ✅ Sanitización automática de secrets en logs
- ✅ Detección de patrones de API keys/tokens
- ✅ Enmascaramiento de valores sensibles
- ✅ `SecureFormatter` para logging.Logger
- ✅ Diccionarios sanitizados automáticamente

**Uso:**
```python
from app.core.secure_logging import get_secure_logger

logger = get_secure_logger(__name__)
logger.info(f"API Key: {api_key}")  # Se sanitiza automáticamente
# Output: "API Key: ***"
```

### 2. Variables de Entorno

**Coolify Configuration:**
Todas las variables sensibles están configuradas en Coolify Environment Variables:

- `AZURE_SPEECH_KEY`
- `GROQ_API_KEY`
- `TELNYX_API_KEY`
- `TWILIO_AUTH_TOKEN`
- `ADMIN_API_KEY`
- `POSTGRES_PASSWORD`

**NUNCA** hardcodear estos valores en código.

### 3. Protección en Git

**.gitignore incluye:**
```
.env
.env.local
.env.*.local
*.key
*.pem
secrets/
credentials/
*.log
logs/
```

**Archivos creados:**
- `.env.example` - Template SIN valores reales ✅
- `.env.local.template` - Template para desarrollo local

### 4. Código Sanitizado

**Eliminado de `main.py`:**
```python
# ANTES (❌ INSEGURO)
print(f"TELNYX_API_KEY: {os.getenv('TELNYX_API_KEY')[:20]}...")

# DESPUÉS (✅ SEGURO)
logger.info(f"Telnyx API configured: {bool(settings.TELNYX_API_KEY)}")
```

## 📋 Checklist de Seguridad

### Para Desarrollo Local

- [ ] 1. Copiar `.env.example` a `.env`
- [ ] 2. Rellenar `.env` con valores reales
- [ ] 3. NUNCA commitear `.env`
- [ ] 4. Usar `secure_logger` en lugar de `print()`
- [ ] 5. No loggear valores directos de secrets

### Para Deployment en Coolify

- [ ] 1. Configurar Environment Variables en Coolify dashboard
- [ ] 2. NO incluir `.env` en el repositorio
- [ ] 3. Verificar que `.gitignore` incluye `.env`
- [ ] 4. Rotar keys cada 90 días
- [ ] 5. Habilitar 2FA en cuentas de servicio

### Para Code Reviews

- [ ] 1. Buscar prints de API keys: `grep -r "print.*API_KEY"`
- [ ] 2. Verificar logs: `grep -r "logger.*api_key"`
- [ ] 3. Buscar hardcoded secrets: `grep -r "sk-[a-z0-9]"`
- [ ] 4. Verificar .gitignore actualizado
- [ ] 5. Confirmar uso de `secure_logger`

## 🔒 Comandos de Verificación

### Buscar Exposición de Secrets en Código

```bash
# Buscar prints de keys
grep -rn "print.*API_KEY\|print.*TOKEN\|print.*PASSWORD" app/

# Buscar valores hardcoded
grep -rn "sk-[a-z0-9]\|key_[a-z0-9]\|Bearer [a-z0-9]" app/

# Verificar que .env no está en Git
git ls-files | grep "\.env$"
# Output esperado: (vacío)
```

### Verificar Sistema de Logging

```bash
# Test de sanitización
python -c "from app.core.secure_logging import sanitize_log_message; print(sanitize_log_message('API Key: sk-12345'))"
# Output esperado: "api_key=***"
```

### Verificar Variables de Entorno

```bash
# En Coolify
# 1. Ir a Environment Variables
# 2. Verificar que todas las keys requeridas están configuradas
# 3. Verificar que los valores NO aparecen en logs
```

## 🚨 Qué Hacer si se Expone un Secret

### Respuesta Inmediata

1. **Revocar la key expuesta inmediatamente**
   - Azure: https://portal.azure.com
   - Groq: https://console.groq.com/keys
   - Telnyx: https://telnyx.com/
   - Twilio: https://www.twilio.com/console

2. **Generar nueva key**

3. **Actualizar en Coolify**
   - Environment Variables → Edit → Save → Restart

4. **Buscar uso no autorizado**
   - Revisar logs de API usage
   - Verificar facturas
   - Revisar audit logs

5. **Notificar al equipo**

6. **Documentar el incidente**

### Prevención

1. **Habilitar alertas**
   - Azure: Budget alerts
   - Groq: Usage alerts
   - Telnyx/Twilio: Anomaly detection

2. **Rotación regular**
   - Calendario de 90 días
   - Scripts automatizados

3. **Git hooks**
   - pre-commit: Buscar secrets
   - CI/CD: Escaneo con `gitleaks` o `truffleHog`

## 📦 Configuración en Coolify

### Paso a Paso

1. **Abrir Coolify Dashboard**
   ```
   https://tu-coolify-dominio.com
   ```

2. **Seleccionar Proyecto**
   - Navegar a "Asistente Andrea"

3. **Environment Variables**
   - Click en "Environment Variables"
   - Click en "Add Variable"

4. **Añadir cada variable:**

   ```
   Name: AZURE_SPEECH_KEY
   Value: [pegar key real]
   ☑ Secret (marcar checkbox)
   ```

   ```
   Name: GROQ_API_KEY
   Value: [pegar key real]
   ☑ Secret
   ```

   ```
   Name: TELNYX_API_KEY
   Value: [pegar key real]
   ☑ Secret
   ```

   ```
   Name: ADMIN_API_KEY
   Value: [generar con: python -c "import secrets; print(secrets.token_urlsafe(32))"]
   ☑ Secret
   ```

5. **Guardar y Restart**
   - Click "Save"
   - Click "Restart Application"

## 🔍 Auditoría de Seguridad

### Ejecutar Regularmente

```bash
# Test 1: Verificar que no hay secrets en código
python -c "
import re
import os
for root, dirs, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path) as f:
                content = f.read()
                if re.search(r'sk-[a-z0-9]{20,}', content, re.I):
                    print(f'ALERT: Possible secret in {path}')
"

# Test 2: Verificar .env en .gitignore
grep "^\.env$" .gitignore || echo "WARNING: .env not in .gitignore"

# Test 3: Test de sanitización
python app/core/secure_logging.py
```

## 📚 Referencias

- [OWASP Secret Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)

## 🆘 Contactos de EmergenciaEn caso de compromiso de secrets:

1. **Revocar keys inmediatamente**
2. **Contactar a:**
   - Azure Support
   - Groq Support
   - Telnyx/Twilio Support
3. **Revisar billing/usage**
4. **Documentar incidente**

---

**Última actualización:** 2026-01-06  
**Versión:** 1.0  
**Status:** ✅ Implementado - Todos los secrets protegidos
