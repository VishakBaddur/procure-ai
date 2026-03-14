#!/bin/bash

# Start Backend Server using system Python

cd backend || exit 1

echo "Installing dependencies..."
# Prefer pip3, fall back to pip
if command -v pip3 >/dev/null 2>&1; then
  pip3 install -r requirements.txt
else
  pip install -r requirements.txt
fi

echo "Starting backend server on http://localhost:8000"
python3 main.py

