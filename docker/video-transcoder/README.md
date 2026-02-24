# 🎬 Video Transcoder

A versatile video transcoding service that converts videos to various formats using FFmpeg, accessible via a web UI and a REST API.

![Docker Pulls](https://img.shields.io/docker/pulls/baladockerbytes/mediatools-transcoder)
![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)


## ✨ Features

-   🎞️ **Versatile Video Transcoding** - Supports a wide range of video codecs (H.264, H.265, AV1, VP9), resolutions (up to 4K), sharpening filters, container formats (MP4, MKV, WebM, MOV, AVI), and audio codecs (AAC, MP3, Opus, Vorbis, AC3, FLAC).
-   🧠 **Intelligent Compatibility Handling** - Dynamically adjusts available container and audio codec options in the UI based on selections, ensuring compatible combinations.
-   🔊 **Robust Audio Copy (New!)** - Intelligent mapping system (`FFMPEG_TO_FRONTEND_AUDIO`) and fallback mechanism (e.g., MKV defaults to Opus) for seamless audio handling across containers.
-   ⚙️ **Dynamic Quality Labels** - Video Quality dropdown automatically updates to show actual CRF values per codec (e.g., AV1 shows CRF-34 for Standard).
-   🔌 **REST API & Job Control** - Programmatic access with new **Cancellation Support** (`POST /api/jobs/{id}/cancel`).
-   📊 **Real-time Progress** - WebSocket-based live progress updates with improved parsing reliability.
-   📋 **Queue Management** - Background job processing with a modern **Cancel Job** button in the web interface.
-   🌙 **Modern Web UI** - Beautiful, responsive web interface with drag-and-drop functionality.
-   🐳 **Docker Containerization** - Easy deployment and management via Docker.
-   💾 **In-memory Job Management** - Efficient handling of current transcoding tasks.

## 📋 Prerequisites

-   **Docker** and **Docker Compose** (recommended for running and developing)
-   OR **Python 3.11+** and **FFmpeg** (for local development without Docker)

## 🚀 Quick Start

### Method 1: Run Using Pre-built Image (Recommended)

1. **Pull the Docker image:**
   ```bash
   docker pull baladockerbytes/mediatools-transcoder:latest
   ```

2. **Prepare storage and run:**
   ```bash
   # Create storage directories (E:\test as an example)
   E:\>mkdir test
   E:\>mkdir test\uploads
   E:\>mkdir test\temp
   E:\>mkdir test\outputs

   # Start the container
   docker run -d -p 8000:8000 \
     -v E:/test/:/storage \
     baladockerbytes/video-transcoder:latest
   ```

3. **Access the application:**
   Open your browser and navigate to [http://localhost:8000](http://localhost:8000).

   *(On Windows, use a path like "C:/path/to/your/storage" instead of "$(pwd)/storage". Note that Docker expects forward slashes and absolute paths for Windows volume mounts.)*

### Method 2: Build from Source and Run (Advanced)

1. **Clone the repository and navigate to the transcoder directory:**

   ```bash
   git clone https://github.com/MediaTools-tech/mediatools.git
   cd mediatools/docker/video-transcoder
   ```

2. **Create docker-compose.yml:**

   ```yaml
   version: '3.8'
   services:
     video-transcoder:
       image: baladockerbytes/mediatools-transcoder:latest
       ports:
         - "8000:8000"
       volumes:
          - ./storage:/storage
       restart: unless-stopped
   ```

3. **Start the container:**

   ```bash
   docker-compose up -d
   ```

### Using Docker Run

```bash
E:\>mkdir test
E:\>mkdir test\uploads
E:\>mkdir test\temp
E:\>mkdir test\outputs

docker run -d -p 8000:8000 \
  -v E:/test/:/storage \
  ghcr.io/mediatools-tech/video-transcoder:latest
```

### Customizing Storage Locations

```yaml
# Alternative: Mount specific directories
volumes:
  - ./my_uploads:/storage/uploads    # Custom uploads location
  - ./my_outputs:/storage/outputs    # Custom outputs location
  - ./my_temp:/storage/temp          # Custom temporary files location
```

## 🔌 API Reference

For complete API documentation including all endpoints, request/response schemas, and usage examples, refer to the interactive docs available once the application is running.

### Quick Overview

- **Base URL**: `http://localhost:8000/api`
- **WebSocket**: `ws://localhost:8000/ws`
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc Docs**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

### Key Endpoints

| Category    | Main Endpoints                 | Description                    |
|-------------|--------------------------------|--------------------------------|
| **Transcode** | `POST /api/upload`             | Upload and transcode a video   |
| **Jobs**    | `GET /api/jobs`                | List all active and recent jobs|
|             | `GET /api/jobs/{job_id}`       | Get status of a transcoding job|
|             | `GET /api/jobs/{job_id}/download`| Download transcoded video file |
| **System**  | `GET /api/health`              | Health check for the API       |

### Quick Examples

**Start a transcoding job:**

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/video.mp4" \
  -F "video_codec=h264" \
  -F "container_format=mp4"
```

**Check job status:**

```bash
curl "http://localhost:8000/api/jobs/your_job_id"
```

**Real-time updates:**

```javascript
// WebSocket connection for live progress
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    console.log('Update:', JSON.parse(event.data));
};
```

## 📁 Directory Structure

### Inside Container

```
/storage/                # Main data directory
├── uploads/            # Uploaded files for transcoding
├── outputs/            # Transcoded output files
└── temp/               # Temporary files during transcoding
```

### On Your Host System

By default, all data is stored in a single `./storage` folder that is mounted to `/storage` inside the container. You can customize this by modifying the volume mounts.

## 🛠️ Development

### Building from Source

```bash
# Clone the repository
git clone https://github.com/MediaTools-tech/mediatools.git
cd mediatools/docker/video-transcoder

# Build the Docker image
docker build -t mediatools-transcoder .

# Run with development mounts
docker run -d -p 8000:8000 \
  -v "$(pwd)/storage":/storage \
  -v "$(pwd)/api":/app/api \
  -v "$(pwd)/frontend":/app/frontend \
  mediatools-transcoder
```

### Project Structure

For a detailed breakdown of the project's folder organization, refer to the [Directory Structure](#directory-structure) section.



## 🎛️ Settings

The transcoder provides various settings that can be configured to control the transcoding process. These are typically managed through the web UI, but some core behaviors can be influenced by environment variables (see Configuration section).

### Transcoding Configuration

- **Video Codec**: Select desired video encoding format (e.g., H.264, H.265).
- **Audio Codec**: Choose audio encoding format (e.g., AAC, MP3).
- **Container Format**: Specify the output file container (e.g., MP4, MKV).
- **Resolution**: Set the output video resolution.
- **Quality (CRF)**: Adjust Constant Rate Factor for video quality control.
- **Sharpening**: Apply sharpening filters to the output video.
- **Output Directory**: Configure the destination for transcoded files.

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | `UTC` | Timezone for timestamps |
| `DEBUG` | `false` | Enable debug logging |
| `APP_NAME` | `Video Transcoder` | Application name displayed in UI |
| `FFMPEG_PATH` | `ffmpeg` | Path to the FFmpeg executable (usually "ffmpeg" if installed and in PATH) |

## ❓ Troubleshooting

### Common Issues

**Permission Errors:**

```bash
# Fix directory permissions (replace /path/to/your/storage with your actual host path)
chmod -R 755 /path/to/your/storage
```

**Container Won't Start:**

```bash
# Check logs
docker logs mediatools-transcoder

# Check if port is available
docker ps | grep :8000
```

**Transcoding Failing:**

- Ensure FFmpeg is correctly configured (environment variable `FFMPEG_PATH`).
- Verify input file is not corrupted.
- Check container logs for FFmpeg errors.
- Ensure sufficient disk space in mounted output and temp directories.

### Getting Help

- Review GitHub Issues: <https://github.com/MediaTools-tech/mediatools/issues>
- Ensure you're using the latest image: `docker pull baladockerbytes/mediatools-transcoder:latest`

## 🙏 Credits

This project builds upon amazing open-source tools:

- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern web framework
- **[FFmpeg](https://ffmpeg.org/)** - The backbone of media processing and conversion

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

## 👥 Contributing

We welcome contributions! Please refer to the [Contributing Guide](CONTRIBUTING.md) (to be created) for more details.

## 📧 Contact

## 📧 Contact

Your Name - your.email@example.com

## 📍 Links

- **Docker Hub**: `baladockerbytes/mediatools-transcoder:latest`
- **GitHub**: <https://github.com/MediaTools-tech/mediatools/tree/main/docker/video-transcoder>
- **Issues**: <https://github.com/MediaTools-tech/mediatools/issues>
