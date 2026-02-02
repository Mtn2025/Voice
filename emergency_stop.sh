#!/bin/bash
# emergency_stop.sh
# DETIENE TODAS LAS OPERACIONES INMEDIATAMENTE
# Uso: ./emergency_stop.sh

echo "🚨 EMERGENCY STOP SEQUENCE INITIATED 🚨"
echo "========================================="

# 1. Capture Diagnostics (Snapshot before kill)
echo "📸 Capturing Metrics Snapshot..."
curl -s http://localhost:8000/api/system/health > system_health_dump.json
curl -s http://localhost:8000/metrics > metrics_dump.txt

# 2. HARD STOP: Kill python processes
echo "🔪 Terminating Application Processes..."

# Find PIDs for uvicorn/main.py
# Note: Adjust logic for Windows (taskkill) vs Linux (pkill)
# Since environment implies Windows (PowerShell/Bash capable)
# using aggressive kill pattern.

# Try graceful first
pkill -f "uvicorn"
pkill -f "main.py"

sleep 2

# Force kill if still alive
pkill -9 -f "uvicorn"
pkill -9 -f "main.py"

# Windows Fallback (common in mixed dev environments)
taskkill //F //IM python.exe //FI "WINDOWTITLE eq Voice Orchestrator*" 2>/dev/null
taskkill //F //IM uvicorn.exe 2>/dev/null

echo "✅ All processes terminated."

# 3. Notify Admin (Simulated Webhook)
echo "📢 Sending Alert Webhook..."
# curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK \
#      -H 'Content-type: application/json' \
#      --data '{"text":"🚨 EMERGENCY STOP TRIGGERED: Architecture Logic Failure Detected."}'

echo "========================================="
echo "🛑 SYSTEM HALTED. CHECK LOGS."
