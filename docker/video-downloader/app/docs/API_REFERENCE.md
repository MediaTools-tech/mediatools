# API Reference for Video Downloader Docker

This document provides a comprehensive reference for the REST API and WebSocket interface exposed by the Video Downloader Docker application. This API allows for programmatic control and monitoring of download tasks, settings, and system status.

## Base URL

The base URL for the REST API is typically `http://localhost:8000/api`.
The WebSocket endpoint is typically `ws://localhost:8000/ws`.

## Authentication

Currently, the API does not implement explicit authentication. It is assumed that access to the API is controlled by network access to the Docker container. For deployments exposed to the internet, it is recommended to secure access through a reverse proxy with authentication.

## API Endpoints

### Downloads API

**Purpose**: Manage video and audio download operations.

| Endpoint                  | Method | Description                               | Request Body (Example)                               | Response Body (Example)                                                                  |
| :------------------------ | :----- | :---------------------------------------- | :--------------------------------------------------- | :--------------------------------------------------------------------------------------- |
| `/api/download`           | `POST` | Start a new download task.                | `{ "url": "https://example.com/video", "type": "video" }` | `{ "success": true, "message": "Download started for https://example.com/video" }`       |
| `/api/download/cancel`    | `POST` | Cancel the currently active download.     | `(None)`                                             | `{ "success": true, "message": "Download cancelled" }`                                   |
| `/api/download/pause`     | `POST` | Pause the currently active download.      | `(None)`                                             | `{ "success": true, "message": "Download paused" }`                                      |
| `/api/download/resume`    | `POST` | Resume a paused download.                 | `(None)`                                             | `{ "success": true, "message": "Download resumed" }`                                     |
| `/api/download/status`    | `GET`  | Get the current status of the downloader. | `(None)`                                             | `{ "status": "downloading", "progress": 50, "speed": "1.2MB/s", "eta": "00:01:30" }` |

### Queue API

**Purpose**: Manage the queue of URLs waiting to be processed.

| Endpoint                  | Method   | Description                                           | Request Body (Example)                    | Response Body (Example)                                 |
| :------------------------ | :------- | :---------------------------------------------------- | :---------------------------------------- | :------------------------------------------------------ |
| `/api/queue`              | `GET`    | List all URLs currently in the queue.                 | `(None)`                                  | `[ { "url": "https://url1", "type": "video" } ]`        |
| `/api/queue`              | `POST`   | Add a new URL to the download queue.                  | `{ "url": "https://url_to_add", "type": "audio" }` | `{ "success": true, "message": "URL added to queue" }`  |
| `/api/queue/{url_b64}`    | `DELETE` | Remove a specific URL from the queue.                 | `(None)`                                  | `{ "success": true, "message": "URL removed from queue" }` |
| `/api/queue/failed`       | `GET`    | List all URLs that previously failed to download.     | `(None)`                                  | `[ { "url": "https://failed_url", "error": "Reason" } ]` |
| `/api/queue/retry/{url_b64}` | `POST` | Retry a failed download by its URL.                   | `(None)`                                  | `{ "success": true, "message": "Failed URL added to queue for retry" }` |
| `/api/queue/history`      | `GET`    | Get a list of all completed download history entries. | `(None)`                                  | `[ { "url": "https://done_url", "filename": "file.mp4" } ]` |

*Note: For `DELETE /api/queue/{url_b64}` and `POST /api/queue/retry/{url_b64}`, the URL should be Base64 encoded if it contains special characters that might interfere with URL routing.*

### Settings API

**Purpose**: Retrieve and update application settings.

| Endpoint            | Method | Description                                 | Request Body (Example)                 | Response Body (Example)                          |
| :------------------ | :----- | :------------------------------------------ | :------------------------------------- | :----------------------------------------------- |
| `/api/settings`     | `GET`  | Get all current application settings.       | `(None)`                               | `{ "download_speed": "5M", ... }`                |
| `/api/settings`     | `PUT`  | Update one or more application settings.    | `{ "settings": { "download_speed": "10M" } }` | `{ "success": true, "message": "Settings updated" }` |
| `/api/settings/reset` | `POST` | Reset all application settings to defaults. | `(None)`                               | `{ "success": true, "message": "Settings reset" }` |

### System API

**Purpose**: Interact with the system for file access and application control.

| Endpoint                  | Method | Description                                  | Request Body (Example) | Response Body (Example)                                |
| :------------------------ | :----- | :------------------------------------------- | :--------------------- | :----------------------------------------------------- |
| `/api/system/open/downloads` | `GET`  | Open the downloads folder on the host system. | `(None)`               | `{ "success": true, "message": "Opened downloads folder" }` |
| `/api/system/open/docs`   | `GET`  | Open the documentation folder on the host system. | `(None)`               | `{ "success": true, "message": "Opened docs folder" }` |
| `/api/system/play-latest` | `GET`  | Play the most recently downloaded media file. | `(None)`               | `{ "success": true, "message": "Playing latest media" }` |
| `/api/system/exit`        | `POST` | Gracefully shut down the application.        | `(None)`               | `{ "success": true, "message": "Shutting down" }`    |
| `/api/system/health`      | `GET`  | Perform a health check on the application.   | `(None)`               | `{ "status": "healthy", "uptime": "..." }`           |

## WebSocket Interface

**Endpoint**: `ws://localhost:8000/ws`

**Purpose**: Provides real-time updates regarding download progress, queue changes, and application status.

Clients can connect to this WebSocket endpoint to receive live notifications. The messages are JSON-formatted and typically contain a `type` field to indicate the nature of the update (e.g., `status_update`, `queue_update`, `download_complete`, `download_failed`).

**Example WebSocket Message**:

```json
{
    "type": "status_update",
    "status": "downloading",
    "message": "Downloading: My Awesome Video",
    "progress": {
        "percentage": 50.5,
        "speed": "2.5MB/s",
        "eta": "00:00:45",
        "filename": "My Awesome Video.mp4",
        "downloaded_bytes": 12345678,
        "total_bytes": 24691356
    }
}
```

This comprehensive API allows for full control and monitoring of the Video Downloader Docker application programmatically.
