#!/bin/bash
set -e  # Exit on error

echo "Initializing storage structure..."

# Create subdirectories if they don't exist
mkdir -p /storage/{downloads,data,docs,bin}

# Copy docs from image to volume if volume docs is empty
if [ -z "$(ls -A /storage/docs 2>/dev/null)" ]; then
    echo "Copying documentation files to volume..."
    cp -r /app/app/docs/* /storage/docs/ 2>/dev/null || echo "No docs to copy" 
else
    echo "Documentation files already exist in volume"
fi

echo "Checking for yt-dlp and spotdl updates..."
pip install --upgrade --no-cache-dir yt-dlp spotdl || echo "Warning: Update failed"

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000