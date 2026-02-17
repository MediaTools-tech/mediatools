#!/bin/bash
set -e  # Exit on error

echo "Initializing storage structure..."

# Create subdirectories if they don't exist
mkdir -p /app/storage/uploads /app/storage/outputs /app/storage/temp

# Fix ownership for mounted volumes (runs as root, then drops to appuser)
chown -R appuser:appuser /app/storage

echo "Starting Video Transcoder..."
exec gosu appuser uvicorn api.main:app --host 0.0.0.0 --port 8000
