#!/bin/bash
# undo_cleanup.sh
# Revierte los cambios de limpieza restaurando los archivos desde git

echo "Restoring files..."
git checkout app/core/orchestrator_v2.py
git checkout app/adapters/outbound/tts/elevenlabs_tts_adapter.py
git checkout app/adapters/outbound/stt/azure_stt_adapter.py

echo "Cleanup undone."
