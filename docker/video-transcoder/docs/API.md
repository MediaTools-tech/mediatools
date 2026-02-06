# Video Transcoder API Documentation

This document provides a brief overview of the Video Transcoder's REST API endpoints. For comprehensive and interactive documentation, please refer to the automatically generated Swagger UI and ReDoc pages when the application is running.

## Base URL

The API is served at `http://localhost:8000/api` (when running locally).

## Interactive API Documentation

Access the interactive API documentation at:
-   **Swagger UI**: `http://localhost:8000/docs`
-   **ReDoc**: `http://localhost:8000/redoc`

## Endpoints

### 1. Upload and Transcode Video

**`POST /api/upload`**

Uploads a video file and initiates a transcoding job with specified options.

-   **Request Body:** `multipart/form-data`
    -   `file`: The video file to upload.
    -   `options`: A JSON string containing transcoding options. See `TranscodingOptions` model below for details.

-   **Response:** `200 OK`
    -   Returns a `JobResponse` object with the `job_id` and initial status.

### 2. Get Job Status

**`GET /api/jobs/{job_id}`**

Retrieves the current status and details of a specific transcoding job.

-   **Path Parameters:**
    -   `job_id`: The unique identifier of the job.

-   **Response:** `200 OK`
    -   Returns a `JobResponse` object.
-   **Error:** `404 Not Found` if `job_id` does not exist.

### 3. List All Jobs

**`GET /api/jobs/`**

Lists all active and recent transcoding jobs.

-   **Query Parameters (Optional):**
    -   `status`: Filter jobs by their status (e.g., `queued`, `processing`, `completed`, `failed`).
    -   `limit`: Maximum number of jobs to return (default: 50).

-   **Response:** `200 OK`
    -   Returns a `JobListResponse` object containing a list of `JobResponse` objects.

### 4. Download Transcoded Video

**`GET /api/jobs/{job_id}/download`**

Downloads the transcoded video file once the job is completed.

-   **Path Parameters:**
    -   `job_id`: The unique identifier of the job.

-   **Response:** `200 OK`
    -   Returns the transcoded video file as a `FileResponse`.
-   **Error:**
    -   `404 Not Found` if `job_id` does not exist or the output file is not found.
    -   `400 Bad Request` if the job is not yet completed.

### 5. Health Check

**`GET /api/health`**

Checks the health and status of the API service.

-   **Response:** `200 OK`
    -   Returns a `HealthResponse` object indicating the service status and FFmpeg availability.

## Transcoding Options (`options` JSON string for `POST /api/upload`)

The `options` parameter in the `POST /api/upload` request body expects a JSON string representing the `TranscodingOptions` model.

Example JSON structure for `options`:

```json
{
    "video_codec": "h265",
    "resolution": "1080p",
    "sharpening": "adaptive",
    "container": "mkv",
    "audio_codec": "opus",
    "crf": 23
}
```

### Available Options:

-   **`video_codec`**: (`string`, default: `"default"`)
    -   `"default"` (maps to H.264)
    -   `"h264"`
    -   `"h265"`
    -   `"av1"`
    -   `"vp9"`
-   **`resolution`**: (`string`, default: `"default"`)
    -   `"default"` (keeps original resolution)
    -   `"auto"` (auto-selects nearest standard resolution)
    -   `"480p"`
    -   `"720p"`
    -   `"1080p"`
    -   `"1440p"`
    -   `"4k"`
-   **`sharpening`**: (`string`, default: `"none"`)
    -   `"none"`
    -   `"light"`
    -   `"medium"`
    -   `"strong"`
    -   `"adaptive"`
-   **`container`**: (`string`, default: `"default"` (maps to MP4))
    -   `"default"`
    -   `"mp4"`
    -   `"mkv"`
    -   `"avi"`
    -   `"webm"`
    -   `"mov"`
-   **`audio_codec`**: (`string`, default: `"default"` (maps to AAC))
    -   `"default"`
    -   `"copy"` (attempts to copy original audio if compatible, otherwise transcodes to a compatible default)
    -   `"aac"`
    -   `"mp3"`
    -   `"opus"`
    -   `"ac3"`
    -   `"flac"`
    -   `"vorbis"`
-   **`crf`**: (`integer`, default: `23`, range: `0-51`)
    -   Video Constant Rate Factor. Lower values mean higher quality and larger file sizes.
    -   `20` for Best Quality
    -   `23` for Standard Quality
    -   `27` for Low Quality
