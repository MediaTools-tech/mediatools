# 🚀 Quick Start - Video Transcoder (Phase 1)

This document provides a quick guide to get the Video Transcoder application up and running.
This is Phase 1 of the application, primarily designed for local machine usage. The Docker image is intended to be pushed to Docker Hub for easy deployment and access.

## 🎯 Key Targets for Phase 1

-   **Standalone Local Application:** Optimized for single-user operation on a local machine.
-   **Enhanced Transcoding Options:** Supports various video/audio codecs, resolutions, and container formats with smart compatibility handling.
-   **Robust Audio Handling**: Intelligent "Copy Original" logic with fallback support (e.g., Opus for MKV).
-   **Task Management**: Real-time progress tracking and **Job Cancellation** support.
-   **Docker Image Distribution:** Designed for easy distribution and deployment via Docker Hub.

## ⏱️ 3-Minute Setup

### Prerequisites
-   **Docker** installed (for running the Docker image)
-   **Docker Compose** installed (for local development, or if you prefer `docker-compose` for running the image)
-   OR **Python 3.11+** and **FFmpeg** (for local development without Docker)

### Option 1: Run with Docker (Recommended for Users)

This method uses a pre-built Docker image, ideal for users who just want to run the application.

1.  **Pull the Docker image:**
    ```bash
    docker pull your-docker-hub-username/video-transcoder:latest
    ```
    (Replace `your-docker-hub-username` with the actual username where the image is pushed.)

2.  **Create local storage directories:**
    These directories will be mounted into the Docker container to persist your uploaded and transcoded video files.
    ```bash
    mkdir -p storage/{uploads,outputs,temp}
    ```

3.  **Run the Docker container:**
    ```bash
    docker run -d -p 8000:8000 -v "$(pwd)/storage":/app/storage your-docker-hub-username/video-transcoder:latest
    ```
    -   `-d`: Runs the container in detached mode (in the background).
    -   `-p 8000:8000`: Maps port 8000 on your host to port 8000 in the container.
    -   `-v "$(pwd)/storage":/app/storage`: Mounts your local `storage` directory to `/app/storage` inside the container. This ensures your files are saved and persist even if the container is removed. On Windows, use `"%cd%\storage"` instead of `$(pwd)/storage`.

4.  **Open browser:**
    Access the web application at: `http://localhost:8000`

### Option 2: Local Development with Docker Compose (Recommended for Developers)

This method builds and runs the application using Docker Compose, which is convenient for development as it provides hot-reloading.

1.  **Navigate to project directory:**
    ```bash
    cd video-transcoder
    ```

2.  **Create environment file:**
    ```bash
    cp .env.example .env
    ```

3.  **Create storage directories:**
    ```bash
    mkdir -p storage/{uploads,outputs,temp}
    touch storage/uploads/.gitkeep storage/outputs/.gitkeep storage/temp/.gitkeep
    ```

4.  **Start application:**
    ```bash
    docker-compose up --build
    ```

5.  **Open browser:**
    Access the web application at: `http://localhost:8000`

### Option 3: Local Development (Without Docker)

1.  **Install FFmpeg:**
    ```bash
    # Ubuntu/Debian
    sudo apt-get install ffmpeg

    # macOS
    brew install ffmpeg
    ```

2.  **Setup Python environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create storage:**
    ```bash
    mkdir -p storage/{uploads,outputs,temp}
    ```

5.  **Create `.env` file:**
    ```bash
    cp .env.example .env
    ```

6.  **Run application:**
    ```bash
    uvicorn api.main:app --reload
    ```

7.  **Open browser:**
    Access the web application at: `http://localhost:8000`

---

## 🎮 Using the Web UI

1.  Open `http://localhost:8000` in your web browser.
2.  **Upload a Video:** Click on the upload area or drag and drop a video file onto it.
3.  **Select Transcoding Settings:**
    *   Choose between "Use default settings" (which transcodes to a standard H.264 MP4 with AAC audio at CRF 23) or "Use custom settings".
    *   If "Use custom settings" is selected, adjust your preferences for:
        *   **Video Codec:** (e.g., H.264, H.265, AV1, VP9)
        *   **Resolution:** (e.g., Keep Original, Auto, 1080p, 4K)
        *   **Sharpening:** (e.g., None, Light, Adaptive)
        *   **Container:** (e.g., MP4, MKV, WebM, MOV, AVI) - options will dynamically update based on selected Video Codec.
        *   **Audio Codec:** (e.g., AAC, MP3, Opus, Copy Original) - options will dynamically update based on selected Container.
        *   **Video Quality:** (Standard (CRF 23), Best Quality (CRF 20), Low Quality (CRF 27))
4.  **Start Transcoding:** Click the "Upload & Transcode" button.
5.  **Monitor Progress:** The webpage will display real-time transcoding progress.
6.  **Download Result:** Once completed, a "Download Transcoded Video" button will appear. Click it to save your file.

## 📚 API Documentation

The REST API endpoints are documented using Swagger UI and ReDoc. Once the application is running, visit:
-   **Swagger UI**: `http://localhost:8000/docs`
-   **ReDoc**: `http://localhost:8000/redoc`

**Key Endpoints to explore:**
-   `POST /api/upload`: Upload and transcode a video with customizable options.
-   `GET /api/jobs/{job_id}`: Get the status of a specific transcoding job.
-   `GET /api/jobs/`: List all active and recent jobs.
-   `GET /api/jobs/{job_id}/download`: Download the transcoded video file.
-   `GET /api/health`: Health check for the API.

---

## 📊 Verify Everything Works

### ✅ Checklist
-   [ ] Application starts without errors in chosen method (Docker Run, Docker Compose, or Local Dev)
-   [ ] Web UI loads at `http://localhost:8000`
-   [ ] Health check (`http://localhost:8000/api/health`) returns "healthy"
-   [ ] Can upload a video file
-   [ ] Transcoding settings (custom/default) behave as expected
-   [ ] Dynamic compatibility filters for codecs/containers/audio work correctly
-   [ ] **CRF Values**: Quality labels show actual CRF values based on selected codec
-   [ ] **Audio Log**: FFmpeg output shows "Copying audio" or valid fallback codec
-   [ ] **Cancellation**: "Cancel Job" button stops encoding and renames file to `_cancelled`
-   [ ] Progress bar updates in real-time with improved parsing
-   [ ] Transcoding completes successfully
-   [ ] Can download transcoded video with correct filename
-   [ ] Jobs list shows recent jobs

### Expected Behavior
1.  **Upload**: File uploads in seconds.
2.  **Processing**: Progress updates every ~2 seconds.
3.  **Completion**: "Download" button appears.
4.  **File Size**: Output should generally be smaller (due to efficient codecs like AV1) or similar depending on settings.

## 🐛 Common Issues & Fixes

| Issue               | Solution                                                                |
|---------------------|-------------------------------------------------------------------------|
| Port 8000 in use    | Change port in `docker-compose.yml` (for compose) or change `-p` mapping (for docker run). |
| FFmpeg not found    | (Local Dev) Install: `sudo apt install ffmpeg` (Ubuntu) or `brew install ffmpeg` (macOS). |
| Permission denied   | Run: `chmod -R 777 storage/` on your host `storage` directory.            |
| Module not found    | (Local Dev) Activate venv: `source venv/bin/activate`.                    |
| Docker build fails  | Run: `docker-compose down -v && docker system prune -a` to clean Docker cache. |
| Docker Hub image not found | Ensure you've replaced `your-docker-hub-username` with the correct value and the image is public. |