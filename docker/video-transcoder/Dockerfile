FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Registry metadata for README synchronization
LABEL org.opencontainers.image.source=https://github.com/MediaTools-tech/mediatools
LABEL org.opencontainers.image.description="Video Transcoder Service"

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY frontend/ ./frontend/
COPY shared/ ./shared/

# Create storage directories
RUN mkdir -p storage/uploads storage/outputs storage/temp

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]