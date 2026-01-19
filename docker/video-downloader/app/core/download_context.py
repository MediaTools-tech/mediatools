"""
Download Context - Dataclass for download state management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from threading import Event
from enum import Enum


class DownloadStatus(str, Enum):
    """Download status states for real-time updates."""
    IDLE = "idle"
    FETCHING_METADATA = "fetching_metadata"
    ANALYZING = "analyzing"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    MERGING = "merging"
    POST_PROCESSING = "post_processing"
    SLEEPING = "sleeping"
    ERROR = "error"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    COMPLETED = "completed"


class DownloadType(str, Enum):
    """Type of download."""
    VIDEO = "video"
    AUDIO = "audio"


@dataclass
class DownloadProgress:
    """Progress information for a download."""
    percentage: float = 0.0
    speed: str = ""
    eta: str = ""
    filename: str = ""
    downloaded_bytes: int = 0
    total_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "percentage": self.percentage,
            "speed": self.speed,
            "eta": self.eta,
            "filename": self.filename,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes
        }


@dataclass
class DownloadContext:
    """Contains all context needed for downloads."""
    
    # Tool paths
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    
    # FFmpeg status
    ffmpeg_status: Dict[str, bool] = field(default_factory=lambda: {
        "available": False,
        "has_libopus": False,
        "has_libvorbis": False
    })
    
    # Folders
    download_folder: str = "/storage/downloads"
    temp_folder: str = "/storage/temp"
    
    # Cancel and Pause events
    cancel_event: Event = field(default_factory=Event)
    cancel_spotdl_event: Event = field(default_factory=Event)
    pause_event: Event = field(default_factory=lambda: Event())
    
    # Initialize pause_event as set (not paused)
    def __post_init__(self):
        self.pause_event.set()
    
    # Current download state
    status: DownloadStatus = DownloadStatus.IDLE
    status_message: str = "Ready"
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    
    # Download info
    current_url: str = ""
    download_type: DownloadType = DownloadType.VIDEO
    video_index: int = 0
    total_videos: int = 0
    current_video_title: str = ""
    is_playlist: bool = False
    
    # Files to clean up on cancel
    stopped_downloads_to_be_deleted: List[str] = field(default_factory=list)
    
    # Error tracking
    last_error: str = ""
    
    def reset(self):
        """Reset context for new download."""
        self.cancel_event.clear()
        self.cancel_spotdl_event.clear()
        self.pause_event.set()  # Ensure not paused
        self.status = DownloadStatus.IDLE
        self.status_message = "Ready"
        self.progress = DownloadProgress()
        self.current_url = ""
        self.video_index = 0
        self.total_videos = 0
        self.current_video_title = ""
        self.is_playlist = False
        self.stopped_downloads_to_be_deleted.clear()
        self.last_error = ""
    
    def set_status(self, status: DownloadStatus, message: str = ""):
        """Update status with optional message."""
        self.status = status
        if message:
            self.status_message = message
        else:
            # Default messages for each status
            messages = {
                DownloadStatus.IDLE: "Ready",
                DownloadStatus.FETCHING_METADATA: "Fetching metadata...",
                DownloadStatus.ANALYZING: "Analyzing streams...",
                DownloadStatus.DOWNLOADING: "Downloading...",
                DownloadStatus.CONVERTING: "Converting...",
                DownloadStatus.MERGING: "Merging streams...",
                DownloadStatus.POST_PROCESSING: "Post-processing...",
                DownloadStatus.SLEEPING: "Rate limited, waiting...",
                DownloadStatus.ERROR: "Error occurred",
                DownloadStatus.CANCELLED: "Cancelled",
                DownloadStatus.PAUSED: "Paused",
                DownloadStatus.COMPLETED: "Completed"
            }
            self.status_message = messages.get(status, str(status))
    
    def update_progress(self, percentage: float = None, speed: str = None, 
                       eta: str = None, filename: str = None,
                       downloaded_bytes: int = None, total_bytes: int = None):
        """Update progress information."""
        if percentage is not None:
            self.progress.percentage = percentage
        if speed is not None:
            self.progress.speed = speed
        if eta is not None:
            self.progress.eta = eta
        if filename is not None:
            self.progress.filename = filename
        if downloaded_bytes is not None:
            self.progress.downloaded_bytes = downloaded_bytes
        if total_bytes is not None:
            self.progress.total_bytes = total_bytes
    
    def to_status_dict(self) -> Dict[str, Any]:
        """Convert current state to dictionary for WebSocket broadcast."""
        return {
            "status": self.status.value,
            "status_message": self.status_message,
            "progress": self.progress.to_dict(),
            "current_url": self.current_url,
            "download_type": self.download_type.value,
            "video_index": self.video_index,
            "total_videos": self.total_videos,
            "current_video_title": self.current_video_title,
            "is_playlist": self.is_playlist,
            "last_error": self.last_error
        }
    
    def is_cancelled(self) -> bool:
        """Check if download was cancelled."""
        return self.cancel_event.is_set()
    
    def cancel(self):
        """Cancel current download."""
        self.cancel_event.set()
        self.cancel_spotdl_event.set()
        self.pause_event.set()  # Unblock if paused
        self.set_status(DownloadStatus.CANCELLED)


# Global download context instance
download_context = DownloadContext()
