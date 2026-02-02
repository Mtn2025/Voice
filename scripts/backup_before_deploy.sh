#!/bin/bash

# Configuration
BACKUP_ROOT="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

echo "🚀 Iniciando Backup: $TIMESTAMP"

# Crear directorio
mkdir -p "$BACKUP_DIR"
if [ $? -ne 0 ]; then
    echo "❌ Error creando directorio de backup $BACKUP_DIR"
    exit 1
fi

# 1. Backup de Base de Datos (PostgreSQL)
echo "📦 Respalando Base de Datos..."
if docker compost exec -T db pg_dump -U postgres app > "$BACKUP_DIR/db_backup.sql"; then
    echo "✅ DB Backup OK"
else
    # Fallback for 'docker compose' vs 'docker-compose'
    if docker-compose exec -T db pg_dump -U postgres app > "$BACKUP_DIR/db_backup.sql"; then
        echo "✅ DB Backup OK (via docker-compose)"
    else
        echo "❌ Error en Backup de BD"
        # Continue but warn
    fi
fi

# 2. Exportar Configuración (JSON)
# Primero copiamos el script helper al contenedor si no existe (asumiendo volumen bind o copy on fly)
# O ejecutamos copiando el script y ejecutándolo.
echo "📋 Exportando Configuración..."
# Para robustez, leemos el helper local y lo pipeamos a python dentro del container si es posible, 
# o asumimos que 'scripts/export_config.py' esta mapeado.
# Si no está mapeado, usamos docker cp.

docker cp ./scripts/export_config.py $(docker compose ps -q app):/app/export_config_tmp.py
if docker compose exec -T app python /app/export_config_tmp.py > "$BACKUP_DIR/config_backup.json"; then
    echo "✅ Config Backup OK"
else
     if docker-compose exec -T app python /app/export_config_tmp.py > "$BACKUP_DIR/config_backup.json"; then
        echo "✅ Config Backup OK"
    else
        echo "⚠️ Error exportando configuración JSON (¿El contenedor 'app' está corriendo?)"
    fi
fi
# Limpieza
docker compose exec -T app rm /app/export_config_tmp.py 2>/dev/null || true

# 3. Copia de Logs
echo "📝 Copiando Logs..."
# Asumiendo que los logs están un directorio local mapeado './logs' o se sacan de docker logs
# Copiaremos los logs del contenedor a archivo
docker compose logs app > "$BACKUP_DIR/app.log"
docker compose logs db > "$BACKUP_DIR/db.log"
echo "✅ Logs OK"

echo "✨ Backup completado exitosamente en: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"
