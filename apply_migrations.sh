#!/bin/bash
set -e

echo "🚀 Starting Database Migration..."

# Ensure PYTHONPATH is set so Alembic can find the app module
export PYTHONPATH=$PYTHONPATH:.

# Run Alembic Upgrade
alembic upgrade head

echo "✅ Migrations applied successfully."
