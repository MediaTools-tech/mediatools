#!/bin/bash
set -e  # Exit on error

echo "Initializing storage structure..."

# Create subdirectories if they don't exist
mkdir -p /storage/uploads /storage/outputs /storage/temp

echo "Checking for ffmpeg updates..."
apk update && apk upgrade --no-cache ffmpeg || echo "Warning: ffmpeg update failed"

echo "Starting Video Transcoder..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
