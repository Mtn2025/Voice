#!/bin/bash

# Este script restaura el ÚLTIMO backup disponible en ./backups/

BACKUP_ROOT="./backups"

# Encontrar el directorio más reciente
LATEST_BACKUP=$(ls -td $BACKUP_ROOT/*/ | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ No se encontraron backups en $BACKUP_ROOT"
    exit 1
fi

echo "🔄 Iniciando Rollback usando: $LATEST_BACKUP"
echo "⚠️  ADVERTENCIA: Esto sobrescribirá la base de datos actual. Tienes 5 segundos para cancelar (Ctrl+C)."
sleep 5

# 1. Restaurar Base de Datos
if [ -f "$LATEST_BACKUP/db_backup.sql" ]; then
    echo "📥 Restaurando DB..."
    # Drop/Create trick or just input sql depending on pg_dump format. 
    # Usually pg_dump needs a clean DB or creates creates logic.
    docker compose exec -T db psql -U postgres -d app < "$LATEST_BACKUP/db_backup.sql"
    if [ $? -eq 0 ]; then
        echo "✅ DB Restaurada"
    else
        echo "❌ Falló restauración de DB"
        exit 1
    fi
else
    echo "⚠️ No se encontró db_backup.sql, saltando DB."
fi

# 2. Restaurar Configuración
if [ -f "$LATEST_BACKUP/config_backup.json" ]; then
    echo "📥 Restaurando Configuración..."
    docker cp ./scripts/import_config.py $(docker compose ps -q app):/app/import_config_tmp.py
    
    cat "$LATEST_BACKUP/config_backup.json" | docker compose exec -T app python /app/import_config_tmp.py
    
    if [ $? -eq 0 ]; then
         echo "✅ Configuración Restaurada"
    else
         echo "❌ Falló restauración de Configuración"
    fi
    docker compose exec -T app rm /app/import_config_tmp.py 2>/dev/null || true
else
    echo "⚠️ No se encontró config_backup.json, saltando Config."
fi

# 3. Reiniciar Servicios
echo "🔄 Reiniciando contenedores..."
docker compose restart

echo "✅ Rollback completado."
echo "🔍 Ejecuta ./scripts/verify_backup.sh para comprobar integridad."
