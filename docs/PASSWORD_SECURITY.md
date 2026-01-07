# Password Security Guidelines - Punto A6

## ✅ Passwords Eliminados

**ANTES (INSEGURO):**
```python
POSTGRES_USER: str = "postgres"  # ❌ Hardcoded default
POSTGRES_PASSWORD: str = "postgres"  # ❌ CRITICAL: Insecure default
```

**DESPUÉS (SEGURO):**
```python
POSTGRES_USER: str  # ✅ Required from .env
POSTGRES_PASSWORD: str  # ✅ Required from .env + validation
```

---

## 🔐 Validación Implementada

El sistema ahora valida que:

1. **No estén vacíos** - POSTGRES_USER y POSTGRES_PASSWORD son obligatorios
2. **No usen valores inseguros** - Rechaza: `postgres`, `password`, `123456`, `admin`, `root`
3. **Longitud mínima** - POSTGRES_PASSWORD debe tener al menos 12 caracteres

**Error si se usa password inseguro:**
```
pydantic.ValidationError: POSTGRES_PASSWORD is using an insecure default value ('postgres').
Use a strong, unique password. Generate one with:
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

---

## 🛠️ Cómo Generar Password Seguro

### Método 1: Python (Recomendado)
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Output: J8vK2nR4mP9xL5wQ3yT6hS8dF1gH7jN0
```

### Método 2: OpenSSL
```bash
openssl rand -base64 32
# Output: 4Kx9mL2pN8vQ5wT7yR3jS6hF1dG9nM4k==
```

### Método 3: pwgen (Linux)
```bash
pwgen -s 32 1
# Output: xL9mK2nR5vP8wQ4yT7hS3dF6gJ1nM0k
```

---

## 📋 Checklist de Configuración

### Desarrollo Local

1. **Copiar template:**
   ```bash
   cp .env.example .env
   ```

2. **Generar password:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Actualizar .env:**
   ```bash
   POSTGRES_PASSWORD=J8vK2nR4mP9xL5wQ3yT6hS8dF1gH7jN0
   ```

4. **Verificar:**
   - [ ] Password tiene al menos 12 caracteres
   - [ ] Password NO es "postgres", "password", etc.
   - [ ] .env está en .gitignore (no committed)

### Producción (Coolify)

1. **Variables de Entorno en Coolify:**
   - Ir a Application → Environment Variables
   - Agregar: `POSTGRES_PASSWORD` (marcar como Secret)
   - Valor: Password generado (32+ caracteres)

2. **Database Password:**
   - Coolify auto-genera password para PostgreSQL service
   - Copiar de: Database Service → Configuration → Password
   - O generar nuevo con comando arriba

3. **Verificar:**
   - [ ] POSTGRES_PASSWORD set en Coolify (Secret)
   - [ ] Password NO visible en código
   - [ ] .env NO committed a Git

---

## ⚠️ Errors Comunes

### Error 1: Variable no definida
```
pydantic.ValidationError: POSTGRES_USER must be set in environment variables.
```
**Solución:** Crear archivo `.env` con valores requeridos

### Error 2: Password inseguro
```
POSTGRES_PASSWORD is using an insecure default value ('postgres').
```
**Solución:** Usar password fuerte (generar con comando arriba)

### Error 3: Password muy corto
```
POSTGRES_PASSWORD must be at least 12 characters long. Current length: 8.
```
**Solución:** Usar password más largo (recomendado: 32 caracteres)

---

## 🔒 Security Best Practices

1. **✅ NUNCA hardcodear passwords** en código
2. **✅ SIEMPRE usar .env** para secrets locales
3. **✅ NUNCA committed .env** a Git (verificar .gitignore)
4. **✅ ROTAR passwords** cada 90 días
5. **✅ USAR passwords únicos** por ambiente (dev != prod)
6. **✅ MINIMUM 12 caracteres**, recomendado 32
7. **✅ USAR secrets managers** en producción (Vault, AWS Secrets Manager)
8. **✅ VALIDAR en código** que passwords sean seguros

---

## 📝 .env.example Updated

```bash
# DATABASE (PostgreSQL) - Punto A6: REQUIRED, NO DEFAULTS
# CRITICAL: These values are REQUIRED and must be set in .env
# Generate strong password: python -c "import secrets; print(secrets.token_urlsafe(32))"
POSTGRES_USER=postgres
POSTGRES_PASSWORD=CHANGE_THIS_TO_STRONG_RANDOM_PASSWORD_MIN_12_CHARS
```

---

## ✅ Punto A6 Completado

- [x] Passwords hardcoded eliminados de config.py
- [x] Variables POSTGRES_USER y POSTGRES_PASSWORD ahora obligatorias
- [x] Validación de passwords inseguros implementada
- [x] Validación de longitud mínima (12 chars)
- [x] .env.example actualizado con warnings
- [x] Documentación de generación de passwords
- [x] Error messages informativos

**Sistema ahora rechaza cualquier intento de usar passwords inseguros.**
