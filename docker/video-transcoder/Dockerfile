FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Registry metadata for README synchronization
LABEL org.opencontainers.image.source=https://github.com/MediaTools-tech/mediatools
LABEL org.opencontainers.image.description="Video Transcoder Service"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script and set permissions
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Copy application code
COPY api/ ./api/
COPY frontend/ ./frontend/
COPY shared/ ./shared/

# Create storage directories and set permissions
RUN mkdir -p /storage/uploads /storage/outputs /storage/temp && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /storage

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]