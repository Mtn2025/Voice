#!/bin/bash

BACKUP_ROOT="./backups"
LATEST_BACKUP=$(ls -td $BACKUP_ROOT/*/ | head -1)

echo "🔍 Verificando último backup: $LATEST_BACKUP"

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ No hay backups."
    exit 1
fi

# Check DB SQL
if [ ! -f "$LATEST_BACKUP/db_backup.sql" ]; then
    echo "❌ Faltante: db_backup.sql"
    exit 1
fi

if [ ! -s "$LATEST_BACKUP/db_backup.sql" ]; then
    echo "❌ Vacío: db_backup.sql (0 bytes)"
    exit 1
fi

# Check Config JSON
if [ ! -f "$LATEST_BACKUP/config_backup.json" ]; then
    echo "⚠️ Faltante: config_backup.json (Advertencia)"
else
    if [ ! -s "$LATEST_BACKUP/config_backup.json" ]; then
        echo "❌ Vacío: config_backup.json"
        exit 1
    fi
fi

echo "✅ Backup ÍNTEGRO. Listo para restore."
