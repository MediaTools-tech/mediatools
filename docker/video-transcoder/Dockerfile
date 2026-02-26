FROM python:3.12-alpine

# Set critical environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Registry metadata for README synchronization
LABEL org.opencontainers.image.source=https://github.com/MediaTools-tech/mediatools
LABEL org.opencontainers.image.description="Video Transcoder Service"

# 1. Install persistent tools
RUN apk add --no-cache ffmpeg curl bash

WORKDIR /app

# 2. Optimized Build Step
# We combine everything into ONE RUN command so that temporary files 
# created by cargo/pip never get saved to a permanent image layer.
COPY requirements.txt .

RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    cargo \
    && pip install --no-cache-dir -r requirements.txt \
    # IMPORTANT: Manually remove the heavy Rust/Cargo cache
    && rm -rf /root/.cargo /root/.cache \
    && apk del .build-deps

# 3. User setup
# Force UID/GID 1000 (Matches Slim/Standard Linux behavior)
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -S -D -s /bin/bash appuser


# 4. Copy code and entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

COPY api/ ./api/
COPY frontend/ ./frontend/
COPY shared/ ./shared/

# 5. Permission setup
RUN mkdir -p /storage/uploads /storage/outputs /storage/temp && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /storage

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]