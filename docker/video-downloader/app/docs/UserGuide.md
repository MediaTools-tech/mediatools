# User Guide for Mediatools Video Downloader Docker

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Volume Mount Configuration](#volume-mount-configuration)
4. [Web Interface](#web-interface)
5. [Downloading Media](#downloading-media)
6. [Platform Support](#platform-support)
7. [API Usage](#api-usage)
8. [Troubleshooting](#troubleshooting)

## Introduction

The Mediatools Video Downloader Docker is a containerized application that provides a unified interface for downloading video and audio content from over 1000 online platforms. Built with FastAPI and yt-dlp, it offers both web interface and API access.

## Quick Start

### Prerequisites

- Docker or Docker Desktop installed
- 2GB RAM minimum, 4GB recommended
- 1GB free disk space

### Method 1: Run Using Pre-built Image (Recommended)

1. **Pull the Docker image:**

   ```bash
   docker pull baladockerbytes/mediatools-downloader:latest

2. **Run the container**

    docker run -d \
      -p 8000:8000 \
      -v /path/to/your/storage:/storage \
      --name mediatools-downloader \
      baladockerbytes/mediatools-downloader:latest

### Method 2: Build from Source and Run (Advanced)

1. **Create a working directory:**

   ```bash
   mkdir video-downloader
   cd video-downloader
   ```

1. **Create docker-compose.yml:**

   ```yaml
   version: '3.8'
   services:
     video-downloader:
       image: baladockerbytes/mediatools-downloader:latest
       ports:
         - "8000:8000"
       volumes:
          # Single volume mount for all data
          - ./storage:/storage

          # OR separate mounts (if you want flexibility):
          # volumes:
          #   - ./downloads:/storage/downloads
          #   - ./data:/storage/data
          #   - ./docs:/storage/docs
          #   - ./bin:/storage/bin
       restart: unless-stopped
   ```

1. **Start the container:**

   ```bash
   docker-compose up -d
   ```

1. **Access the application:**
   - Web Interface: <http://localhost:8000>
   - API Documentation: <http://localhost:8000/docs>
   - Health Check: <http://localhost:8000/health>

### Changing the Port

If port 8000 is already in use, change it in `docker-compose.yml`:

```yaml
ports:
  - "9000:8000"  # Host:Container
```

Then access at: `http://localhost:9000`

### From Other Devices (Optional)

To access from other devices on your network:

1. Find your computer's IP address
2. Access: `http://[YOUR_IP]:8000`
3. Ensure firewall allows port 8000

## Volume Mount Configuration

### Customizing Download Locations

You can customize where files are stored by modifying volume mounts:

```yaml
# Example: Custom paths for different operating systems

# Windows with specific drive:
volumes:
  - e:/storage:/storage

# Linux with external storage:
volumes:
  - /mnt/nas/storage:/storage

# Mac OS:
volumes:
  - ~/Movies/storage:/storage
```

### Directory Structure

The application stores all data in the `/storage/` directory:

```
Container Path        | Host Path (default) | Purpose
----------------------|---------------------|---------
/storage/downloads    | ./storage/downloads | Downloaded media files
/storage/data         | ./storage/data      | App settings and database
/storage/docs         | ./storage/docs      | Documentation
/storage/bin          | ./storage/bin       | External tools
```

## Web Interface

### Main Dashboard

- **URL Input**: Paste video/audio URLs
- **Queue Management**: View and manage download queue
- **Progress Tracking**: Real-time download progress
- **Quick Actions**: Pause, resume, cancel downloads

### Settings Page

Configure application behavior:

- **Download Settings**: Format, quality, speed limits
- **Audio Extraction**: Output format, bitrate
- **Platform Credentials**: API keys for supported platforms (spotify)
- **Storage Settings**: Download locations and organization

### History Page

- View past downloads (successful/failed)
- Retry failed downloads
- Clear history

## Downloading Media

### Single Downloads

1. Paste URL in the input field
2. Select format (Video or Audio)
3. Click "Download"
4. Monitor progress in the queue

### Batch Downloads

- Add multiple URLs (one per line)
- Process sequentially in queue
- Configure parallel downloads in settings

### Supported Formats

- **Video**: MP4, MKV
- **Audio**: MP3, M4A

## Platform Support

### Public Platforms (No Login Required)

- 1000+ other sites via yt-dlp

### Credential-Based Platforms

- Spotify (requires OAuth setup for playlist metadata)
- SoundCloud (optional login)
- Bandcamp (optional login)

### Platform-Specific Notes

- **Spotify**: Requires client ID/secret setup for downloading metadata

## API Usage

### REST API Endpoints

For complete API documentation including all endpoints, request/response schemas, WebSocket interface, and usage examples, refer to the **[API Reference Documentation](API_REFERENCE.md)**.

### Quick Overview

- **Base URL**: `http://localhost:8000/api`
- **WebSocket**: `ws://localhost:8000/ws`
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Health Check**: `http://localhost:8000/health`

### Key Endpoints

| Category | Main Endpoints | Description |
|----------|----------------|-------------|
| **Downloads** | `POST /api/download` | Start new downloads |
| **Queue** | `GET /api/queue` | Manage download queue |
| **Settings** | `PUT /api/settings` | Configure application |
| **System** | `GET /api/system/health` | Health monitoring |

### Quick Examples

**Start a download:**

```bash
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=example", "format": "video"}'
```

**Check queue status:**

```bash
curl "http://localhost:8000/api/queue"
```

**Real-time updates:**

```javascript
// WebSocket connection for live progress
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    console.log('Update:', JSON.parse(event.data));
};
```

📖 **See the full [API Reference Documentation](API_REFERENCE.md) for complete details, including all endpoints, data models, error codes, and advanced usage.**

## Troubleshooting

### Common Issues

#### Permission Errors

```bash
# Fix directory permissions
sudo chmod 777 ./downloads ./data

# Or run with specific user ID
docker run -u $(id -u):$(id -g) ...
```

#### Container Won't Start

```bash
# Check logs
docker logs video-downloader

# Check port availability
netstat -tulpn | grep :8000
```

#### Downloads Failing

1. Check internet connectivity in container:

   ```bash
   docker exec video-downloader ping google.com
   ```

2. Verify URL is accessible
3. Check available disk space

#### Volume Mount Issues

```bash
# Test volume mount
docker run --rm -v $(pwd)/downloads:/test alpine ls -la /test

# Verify file permissions
docker exec video-downloader ls -la /downloads
```

### Logs and Diagnostics

```bash
# View application logs
docker logs video-downloader

# View logs with follow
docker logs -f video-downloader

# Check container health
docker inspect video-downloader | grep -A 10 Health
```

## Resources

- **Docker Image**: `baladockerbytes/mediatools-downloader:latest`
- **Source Code**: <https://github.com/MediaTools-tech/mediatools/tree/main/docker/video-downloader>
- **Issue Tracking**: <https://github.com/MediaTools-tech/mediatools/issues>
- **yt-dlp Documentation**: <https://github.com/yt-dlp/yt-dlp>
- **FastAPI Documentation**: <https://fastapi.tiangolo.com>

## Support

For support, please:

1. Check the troubleshooting guide above
2. Review documentation in `/docs` directory
3. Search existing issues on GitHub
4. Create a new issue with logs and reproduction steps

---
*Last Updated: January 2026*

```

## **Updated LICENSE.txt** (kept as is since MIT license is correct)

The existing MIT License text is perfect. Just ensure the copyright year is updated:

```txt
MIT License

Copyright (c) 2026 The Video Downloader Docker Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
