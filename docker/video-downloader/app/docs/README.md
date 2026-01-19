# Mediatools Video Downloader Docker 🎬

A modern, containerized video and audio downloader with a beautiful web interface. Download from YouTube, Spotify, and 1000+ other sites.

![Docker Pulls](https://img.shields.io/docker/pulls/baladockerbytes/mediatools-downloader)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

## ✨ Features

- 🎬 **Video Downloads** - Download videos from YouTube, Vimeo, and 1000+ sites via yt-dlp
- 🎵 **Audio Extraction** - Convert videos to MP3, M4A, OPUS, FLAC formats
- 🎧 **Spotify Support** - Download tracks and playlists with metadata
- 📋 **Queue Management** - Add multiple URLs and process them sequentially
- 📊 **Real-time Progress** - WebSocket-based live progress updates
- ⚙️ **Customizable Settings** - Configure formats, quality, download paths
- 📜 **Download History** - Track completed and failed downloads
- 🌙 **Modern Dark UI** - Beautiful, responsive web interface
- 🔌 **REST API** - Programmatic access to all features

## 🚀 Quick Start

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

### Using Docker Run

```bash
# Create storage directory (optional)
mkdir -p storage

# Run the container
docker run -d \
  -p 8000:8000 \
  -v /path/to/your/storage:/storage \
  --name video-downloader \
  baladockerbytes/mediatools-downloader:latest
```

### Customizing Download Locations

```yaml
# Alternative: Mount specific directories
volumes:
  - ./my_downloads:/storage/downloads    # Custom downloads location
  - ./my_data:/storage/data              # Custom settings location
  - ./my_docs:/storage/docs              # Custom docs location
  - ./my_bin:/storage/bin                # External tools
```

## 📁 Directory Structure

### Inside Container

```
/storage/               # Main data directory
├── downloads/          # Downloaded media files
├── data/               # Application settings and database
├── docs/               # Documentation (auto-initialized)
└── bin/                # External tools (deno for Spotify)
```

### On Your Host System

By default, all data is stored in a single `./storage` folder. You can customize this by modifying the volume mounts.

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | `UTC` | Timezone for timestamps |
| `UPGRADE_PACKAGES` | `false` | Auto-update yt-dlp/spotdl on startup |
| `LIMIT_RATE` | (empty) | Download speed limit (e.g., "5M") |

### Custom Volume Mounts Examples

**Windows:**

```bash
docker run -d -p 8000:8000 \
  -v /mnt/e/Downloads/videos:/storage/downloads \
  -v /mnt/e/AppData/video-downloader:/storage/data \
  baladockerbytes/mediatools-downloader:latest
```

**Linux/Mac:**

```bash
docker run -d -p 8000:8000 \
  -v /mnt/nas/downloads:/storage/downloads \
  -v ~/.config/video-downloader:/storage/data \
  baladockerbytes/mediatools-downloader:latest
```

## 🔌 API Reference

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

## 🎛️ Settings

### Download Configuration

- **Format Selection**: Choose video/audio formats and quality
- **Speed Limits**: Set download rate limits
- **Metadata**: Embed thumbnails and metadata
- **Organization**: Auto-create subfolders by platform

### Platform Authentication

For Spotify and other credential-based platforms:

1. Obtain API credentials from the platform's developer portal
2. Enter credentials in the Settings page
3. For Spotify: Metadata extraction requires Client ID and Secret from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

## 🛠️ Development

### Building from Source

```bash
# Clone the repository
git clone https://github.com/MediaTools-tech/mediatools.git
cd mediatools/docker/video-downloader

# Build the Docker image
docker build -t mediatools-downloader .

# Run with development mounts
docker run -d -p 8000:8000 \
  -v $(pwd)/storage:/storage \
  -v $(pwd)/app:/app \
  mediatools-downloader
```

### Project Structure

```
mediatools/docker/video-downloader/
├── Dockerfile              # Container definition
├── docker-compose.yml      # Docker Compose configuration
├── entrypoint.sh           # Container startup script
├── requirements.txt        # Python dependencies
├── storage/                # Default storage location
│   ├── docs/              # Documentation
│   └── (other subdirs)
└── app/                    # Application source code
    ├── main.py            # FastAPI application
    ├── api/               # API endpoints
    ├── core/              # Business logic
    ├── utils/             # Utilities
    ├── static/            # Frontend assets
    └── templates/         # HTML templates
```

**Repository**: <https://github.com/MediaTools-tech/mediatools/tree/main/docker/video-downloader>

## ❓ Troubleshooting

### Common Issues

**Permission Errors:**

```bash
# Fix directory permissions
chmod 755 ./storage
```

**Container Won't Start:**

```bash
# Check logs
docker logs video-downloader

# Check if port is available
docker ps | grep :8000
```

**Downloads Failing:**

- Verify internet connectivity in container
- Check if URL is accessible
- Ensure sufficient disk space

### Getting Help

- Check documentation in `/storage/docs/` after first run
- Review GitHub Issues: <https://github.com/MediaTools-tech/mediatools/issues>
- Ensure you're using the latest image: `docker pull baladockerbytes/mediatools-downloader:latest`

## 📄 License

MIT License - See [LICENSE.txt](LICENSE.txt) for details.

Copyright (c) 2026 The Video Downloader Docker Project

## 🙏 Credits

This project builds upon amazing open-source tools:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Video downloading from 1000+ sites
- **[spotdl](https://github.com/spotDL/spotify-downloader)** - Spotify track downloading
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern web framework
- **[FFmpeg](https://ffmpeg.org/)** - Media processing and conversion
- **[Deno](https://deno.land/)** - yt-dlp dependency (yt-dlp recommended)

## 📍 Links

- **Docker Hub**: `baladockerbytes/mediatools-downloader:latest`
- **GitHub**: <https://github.com/MediaTools-tech/mediatools/tree/main/docker/video-downloader>
- **Issues**: <https://github.com/MediaTools-tech/mediatools/issues>
