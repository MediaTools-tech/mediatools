from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class VideoCodec(str, Enum):
    DEFAULT = "default"
    H264 = "h264"
    H265 = "h265"
    AV1 = "av1"
    VP9 = "vp9"


class Resolution(str, Enum):
    DEFAULT = "default"
    AUTO = "auto"
    P480 = "480p"
    P720 = "720p"
    P1080 = "1080p"
    P1440 = "1440p"
    P4K = "4k"


class Sharpening(str, Enum):
    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    STRONG = "strong"
    ADAPTIVE = "adaptive"


class Container(str, Enum):
    DEFAULT = "default"
    MP4 = "mp4"
    MKV = "mkv"
    AVI = "avi"
    WEBM = "webm"
    MOV = "mov"


class AudioCodec(str, Enum):
    DEFAULT = "default"
    COPY = "copy"
    AAC = "aac"
    MP3 = "mp3"
    OPUS = "opus"
    AC3 = "ac3"
    FLAC = "flac"
    VORBIS = "vorbis"


class TranscodingOptions(BaseModel):
    video_codec: VideoCodec = Field(VideoCodec.DEFAULT, title="Video Codec")
    resolution: Resolution = Field(Resolution.DEFAULT, title="Resolution")
    sharpening: Sharpening = Field(Sharpening.NONE, title="Sharpening Filter")
    container: Container = Field(Container.DEFAULT, title="Container Format")
    audio_codec: AudioCodec = Field(AudioCodec.DEFAULT, title="Audio Codec")
    crf: int = Field(23, ge=0, le=51, title="Video Quality (CRF)")


class JobResponse(BaseModel):
    """Response model for job information"""
    job_id: str
    filename: str
    status: str  # queued, processing, completed, failed
    progress: int  # 0-100
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    input_path: str
    output_path: Optional[str] = None
    file_size_mb: Optional[float] = None
    options: Optional[TranscodingOptions] = None


class JobListResponse(BaseModel):
    """Response model for list of jobs"""
    jobs: List[JobResponse]
    total: int = 0

    def __init__(self, **data):
        super().__init__(**data)
        self.total = len(self.jobs)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    ffmpeg_available: bool