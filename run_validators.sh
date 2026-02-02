#!/bin/bash
# run_validators.sh
# Ejecuta suite de validación de datos

echo "🛡️ Starting Data Integrity Validation Suite..."
echo "============================================"

# 1. Session Validator
check_session=0
if [ -f "VALIDATORS/session_validator.js" ]; then
    node VALIDATORS/session_validator.js
    if [ $? -ne 0 ]; then check_session=1; fi
else
    echo "⚠️ Session Validator missing."
fi

echo "--------------------------------------------"

# 2. Transcription Validator
check_trans=0
if [ -f "VALIDATORS/transcription_validator.js" ]; then
    node VALIDATORS/transcription_validator.js
    if [ $? -ne 0 ]; then check_trans=1; fi
else
    echo "⚠️ Transcription Validator missing."
fi

echo "--------------------------------------------"

# 3. Historical Validator
check_hist=0
if [ -f "VALIDATORS/historical_validator.js" ]; then
    node VALIDATORS/historical_validator.js
    if [ $? -ne 0 ]; then check_hist=1; fi
else
    echo "⚠️ Historical Validator missing."
fi

echo "============================================"
if [ $check_trans -ne 0 ]; then
    echo "❌ VALIDATION FAILED: Critical logic missing."
    exit 1
else
    echo "✅ ALL SYSTEMS GO."
    exit 0
fi
