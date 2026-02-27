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
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    cargo

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

# Registry metadata
LABEL org.opencontainers.image.source=https://github.com/MediaTools-tech/mediatools
LABEL org.opencontainers.image.description="Video Transcoder Service"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/venv \
    PATH="/venv/bin:$PATH"

# Install only the runtime tools needed at run-time (no gcc, no cargo, etc.)
RUN apk add --no-cache ffmpeg curl bash

# Copy the fully-built virtual environment from the builder stage
COPY --from=builder /venv /venv

# User setup — force UID/GID 1000 to match standard Linux behaviour
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -S -D -s /bin/bash appuser

WORKDIR /app

# Copy application code and entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

COPY api/ ./api/
COPY frontend/ ./frontend/
COPY shared/ ./shared/

# Create storage directories and set ownership in one layer
RUN mkdir -p /storage/uploads /storage/outputs /storage/temp && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /storage

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]