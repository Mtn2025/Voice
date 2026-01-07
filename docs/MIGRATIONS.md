# Migraciones de Base de Datos - Guía Completa

## Sistema Implementado: Alembic

**Versión:** 1.17.2  
**Tipo:** Migraciones versionadas con soporte async  
**Estado:** ✅ Configurado y listo

## Migración de Sistema Ad-Hoc a Alembic

### ANTES (❌ Problemático)
```python
# main.py - 70+ líneas de ALTER TABLE ad-hoc
await conn.execute(text("ALTER TABLE...IF NOT EXISTS..."))
await conn.execute(text("ALTER TABLE...IF NOT EXISTS..."))
# ... 30+ migraciones manuales
```

**Problemas:**
- Sin versionamiento
- Sin rollback
- Sin historial de cambios
- Difícil rastrear qué cambios se aplicaron
- No hay control de orden de ejecución  

### DESPUÉS (✅ Solución)
```bash
alembic upgrade head  # Aplicar todas las migraciones
alembic downgrade -1  # Revertir última migración
alembic history       # Ver historial completo
```

## Comandos Principales

### Desarrollo

```bash
# Crear nueva migración (autogenerada)
alembic revision --autogenerate -m "descripción del cambio"

# Crear migración manual
alembic revision -m "descripción del cambio"

# Aplicar migraciones
alembic upgrade head

# Revertir última migración
alembic downgrade -1

# Ver historial
alembic history

# Ver migración actual
alembic current
```

### Producción (Coolify)

```bash
# En el startup de la app, ANTES de iniciar FastAPI:
alembic upgrade head
```

## Estructura de Archivos

```
proyecto/
├── alembic/
│   ├── versions/          # Migraciones versionadas
│   │   └── c9f05c1b0a49_initial_migration.py
│   ├── env.py             # Configuración (async support)
│   └── script.py.mako     # Template para nuevas migraciones
├── alembic.ini            # Configuración de Alembic
└── app/
    └── db/
        └── models.py      # Modelos SQLAlchemy
```

## Migración Inicial Creada

**Archivo:** `c9f05c1b0a49_initial_migration_with_all_existing_.py`

**Contenido:** Refleja el estado actual completo de la base de datos con todas las tablas y columnas.

## Actualización de main.py

**Código removido:**
- ✅ 70+ líneas de ALTER TABLE eliminadas
- ✅ Migraciones ad-hoc eliminadas

**Código añadido:**
```python
# En lifespan, ANTES de Base.metadata.create_all
from alembic import command
from alembic.config import Config

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")
```

## Flujo de Trabajo para Cambios en DB

### 1. Modificar Modelos

```python
# app/db/models.py
class AgentConfig(Base):
    # ... existing fields ...
    new_field = Column(String, default="value")  # AÑADIR NUEVO CAMPO
```

### 2. Generar Migración

```bash
alembic revision --autogenerate -m "add new_field to agent_config"
```

Esto crea:
```
alembic/versions/abc123_add_new_field_to_agent_config.py
```

### 3. Revisar Migración Generada

```python
def upgrade():
    op.add_column('agent_configs', sa.Column('new_field', sa.String(), nullable=True))

def downgrade():
    op.drop_column('agent_configs', 'new_field')
```

### 4. Aplicar Migración

**Local:**
```bash
alembic upgrade head
```

**Coolify:** Se aplica automáticamente en el next deploy.

## Ejemplo: Añadir Nueva Columna

```bash
# 1. Modificar models.py
# class AgentConfig(Base):
#     new_column = Column(Integer, default=0)

# 2. Generar migración
alembic revision --autogenerate -m "add new_column"

# 3. Revisar archivo generado en alembic/versions/

# 4. Aplicar
alembic upgrade head

# 5. Si hay problema, revertir
alembic downgrade -1
```

## Integración con Coolify

### Dockerfile Update

```dockerfile
# Añadir al Dockerfile ANTES de CMD
RUN alembic upgrade head
```

**O en el startup script:**
```bash
#!/bin/bash
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Ventajas del Nuevo Sistema

| Aspecto | Ad-Hoc (Antes) | Alembic (Ahora) |
|---------|----------------|-----------------|
| **Versionamiento** | ❌ No | ✅ Sí |
| **Rollback** | ❌ Imposible | ✅ `alembic downgrade -1` |
| **Historial** | ❌ No existe | ✅ `alembic history` |
| **Orden garantizado** | ❌ No | ✅ Sí |
| **Colaboración** | ❌ Difícil | ✅ Git-friendly |
| **Testing** | ❌ Difícil | ✅ Fácil (test DB) |
| **Producción** | ❌ Manual | ✅ Automático |

## Troubleshooting

### Error: "Target database is not up to date"

```bash
# Ver versión actual
alembic current

# Ver qué falta aplicar
alembic upgrade head
```

### Error: "Can't locate revision"

```bash
# Resetear a estado inicial
alembic stamp head

# O marcar como versión específica
alembic stamp c9f05c1b0a49
```

### Crear migración en ambiente sin DB

```bash
# Usar --sql para generar SQL sin conectar
alembic upgrade head --sql > migration.sql
```

## Mejores Prácticas

1. ✅ **Siempre revisar** migraciones autogeneradas antes de aplicar
2. ✅ **Nombrar descriptivamente:** `add_user_email` no `update_schema`
3. ✅ **Una migración = un cambio conceptual**
4. ✅ **Incluir datos de migración si es necesario:**
   ```python
   def upgrade():
       op.execute("UPDATE users SET status='active' WHERE status IS NULL")
   ```
5. ✅ **Commit migraciones a Git** junto con cambios de modelos
6. ✅ **Testear rollback** en desarrollo
7. ⚠️ **NO editar migraciones ya aplicadas en producción**

## Comandos Avanzados

```bash
# Generar SQL sin ejecutar
alembic upgrade head --sql

# Aplicar hasta versión específica
alembic upgrade abc123

# Ver diferencias
alembic show c9f05c1b0a49

# Merge de branches con conflictos
alembic merge heads -m "merge migrations"
```

---

**Última actualización:** 2026-01-06  
**Versión:** 1.0  
**Status:** ✅ Implementado - Sistema de migraciones versionadas activo
