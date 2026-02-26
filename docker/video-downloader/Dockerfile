FROM python:3.12-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Registry metadata for README synchronization
LABEL org.opencontainers.image.source=https://github.com/MediaTools-tech/mediatools
LABEL org.opencontainers.image.description="Video Downloader Service"

# 1. Install persistent runtime tools
# spotdl/yt-dlp often require these external binaries
RUN apk add --no-cache ffmpeg curl bash

WORKDIR /app

# 2. Optimized Build Step
COPY requirements.txt .

# Install build dependencies, compile wheels, then immediately delete build deps
# Pillow (for image processing) requires build tools on Alpine
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    cargo \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    && pip install --no-cache-dir -r requirements.txt \
    # Clean up the Cargo and Pip caches
    && rm -rf /root/.cargo /root/.cache \
    && apk del .build-deps

# 3. User setup (Matches standard Linux UID/GID 1000)
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -S -D -s /bin/bash appuser

# 4. Copy code and entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

COPY app/ .

# 5. Permission setup
RUN mkdir -p /storage/downloads /storage/data /storage/docs /storage/bin && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /storage

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
