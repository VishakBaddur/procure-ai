#!/bin/bash
# Kill any existing backend server
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Start the backend server
cd "$(dirname "$0")"
python3 main.py

