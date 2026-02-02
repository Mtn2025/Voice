#!/bin/bash
# test_minimal_flow.sh
# Wrapper to run the verification script

echo "🚀 Starting Minimal Flow Verification..."
echo "1. Checking Dependencies..."
# python3 -m pip install websockets asyncio > /dev/null 2>&1

echo "2. Running Simulation..."
python verify_minimal_flow.py

status=$?

if [ $status -eq 0 ]; then
    echo "✅ Minimal Flow Verified!"
else
    echo "❌ Minimal Flow Failed!"
    echo "Report: logic for Post-Call Extraction and Transcript History is MISSING."
fi

exit $status
