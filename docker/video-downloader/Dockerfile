# =============================================================================
# Stage 1: builder
# Installs all build-time dependencies and Python packages.
# This stage is discarded — none of the build tools reach the final image.
# =============================================================================
FROM python:3.12-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create virtual environment and keep it at a well-known path
RUN python -m venv /venv
ENV VIRTUAL_ENV=/venv \
    PATH="/venv/bin:$PATH"

# Install build dependencies (only needed to compile native Python extensions)
# Pillow (for image processing) requires build tools on Alpine
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    cargo \
    jpeg-dev \
    zlib-dev \
    freetype-dev

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cargo /root/.cache \
    && find /venv -type d -name "__pycache__" -exec rm -rf {} +


# =============================================================================
# Stage 2: final
# Clean runtime image — only the venv and necessary runtime tools are included.
# =============================================================================
FROM python:3.12-alpine AS final

# Registry metadata for README synchronization
LABEL org.opencontainers.image.source=https://github.com/MediaTools-tech/mediatools
LABEL org.opencontainers.image.description="Video Downloader Service"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/venv \
    PATH="/venv/bin:$PATH"

# 1. Install persistent runtime tools
# spotdl/yt-dlp often require these external binaries
RUN apk add --no-cache ffmpeg curl bash

# 3. User setup (Matches standard Linux UID/GID 1000)
# We must create the user BEFORE copying the venv so the --chown flag works properly
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -S -D -s /bin/bash appuser

# Copy the fully-built virtual environment from the builder stage
# Set ownership to appuser so they can pip install updates at runtime
COPY --from=builder --chown=appuser:appuser /venv /venv

WORKDIR /app

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
