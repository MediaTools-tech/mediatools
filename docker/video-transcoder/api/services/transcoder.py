import subprocess
import re
import os
import json
from pathlib import Path
from typing import Dict, Tuple, Optional

from api.config import settings
from api.services.storage import get_temp_path, get_unique_output_path, move_temp_to_output, get_file_size_mb
from api.services.job_manager import job_manager
from api.models import TranscodingOptions

# --- Enhanced Transcoder Logic ---

# Configuration presets from video_transcoder_enhanced.py
VIDEO_CODECS = {
    "default": "libx264",
    "h264": "libx264",
    "h265": "libx265",
    "av1": "libaom-av1",
    "vp9": "libvpx-vp9"
}

SHARPENING_FILTERS = {
    "none": None,
    "light": "unsharp=5:5:0.5:5:5:0.0",
    "medium": "unsharp=5:5:1.0:5:5:0.0",
    "strong": "unsharp=5:5:1.5:5:5:0.0",
    "adaptive": "cas=0.5"
}

CONTAINERS = {
    "default": "mp4",
    "mp4": "mp4",
    "mkv": "mkv",
    "avi": "avi",
    "webm": "webm",
    "mov": "mov"
}

AUDIO_CODECS = {
    "aac": "aac",
    "mp3": "libmp3lame",
    "opus": "libopus",
    "vorbis": "libvorbis",
    "ac3": "ac3",
    "flac": "flac"
}

# FFmpeg decoder name → Frontend key (for DETECTION)
# This maps what ffprobe returns to our frontend keys
FFMPEG_TO_FRONTEND_AUDIO = {
    "aac": "aac",
    "mp3": "mp3",
    "mp3float": "mp3",
    "opus": "opus",
    "ac3": "ac3",
    "flac": "flac",
    "vorbis": "vorbis",
    "pcm_s16le": "pcm",
    "pcm_s24le": "pcm",
    "eac3": "ac3",
}

MULTICHANNEL_SUPPORT = {
    "mp4": {"aac": 8, "ac3": 6, "mp3": 2, "copy": None},
    "mkv": {"aac": 8, "ac3": 6, "opus": 8, "vorbis": 8, "flac": 8, "copy": None},
    "avi": {"mp3": 2, "ac3": 6, "copy": None},
    "webm": {"opus": 8, "vorbis": 8, "copy": None},
    "mov": {"aac": 8, "ac3": 6, "mp3": 2, "copy": None}
}

CONTAINER_CODEC_COMPATIBILITY = {
    "mp4": {
        "video": ["libx264", "libx265"],
        "audio": ["aac", "mp3", "ac3"]  # Frontend keys
    },
    "mkv": {
        "video": ["libx264", "libx265", "libvpx-vp9", "libaom-av1"],
        "audio": ["aac", "mp3", "ac3", "opus", "flac", "vorbis"]  # Frontend keys
    },
    "avi": {
        "video": ["libx264"],
        "audio": ["mp3", "ac3"]  # Frontend keys
    },
    "webm": {
        "video": ["libvpx-vp9", "libaom-av1"],
        "audio": ["opus", "vorbis"]  # Frontend keys
    },
    "mov": {
        "video": ["libx264", "libx265"],
        "audio": ["aac", "mp3", "ac3"]  # Frontend keys
    }
}

CRF_QUALITY_MATCHED = {
    'low': {
        'h264': 27,
        'h265': 29,
        'vp9': 37,
        'av1': 39,
    },
    'standard': {
                'h264': 23,
        'h265': 25,
        'vp9': 32,
        'av1': 34,
    },
    'high': {
        'h264': 19,
        'h265': 21,
        'vp9': 27,
        'av1': 29,
    },
    'visually_lossless': {
        'h264': 15,
        'h265': 17,
        'vp9': 23,
        'av1': 24,
    }
}


def get_video_info(input_path: str) -> Optional[Dict]:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(input_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, encoding="utf-8", check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return None

def get_video_duration(video_info: Dict) -> float:
    if not video_info:
        return 0.0
    if "format" in video_info and "duration" in video_info["format"]:
        try:
            return float(video_info["format"]["duration"])
        except (ValueError, TypeError):
            pass
    for stream in video_info.get("streams", []):
        if stream.get("codec_type") == "video":
            duration = stream.get("duration")
            if duration:
                try:
                    return float(duration)
                except (ValueError, TypeError):
                    pass
    return 0.0

def get_audio_channels(video_info: Dict) -> int:
    if not video_info:
        return 2
    for stream in video_info.get("streams", []):
        if stream.get("codec_type") == "audio":
            return stream.get("channels", 2)
    return 2

def get_original_audio_codec(video_info: Dict) -> Optional[str]:
    """Extract original audio codec from video info."""
    if not video_info:
        return None
    for stream in video_info.get("streams", []):
        if stream.get("codec_type") == "audio":
            return stream.get("codec_name")
    return None

def get_video_resolution(video_info: Dict) -> Tuple[int, int]:
    if not video_info:
        return (1920, 1080)
    for stream in video_info.get("streams", []):
        if stream.get("codec_type") == "video":
            width = stream.get("width", 1920)
            height = stream.get("height", 1080)
            return (width, height)
    return (1920, 1080)

def get_nearest_standard_resolution(width: int, height: int) -> str:
    if height <= 480: return "480p"
    elif height <= 720: return "720p"
    elif height <= 1080: return "1080p"
    elif height <= 1440: return "1440p"
    else: return "4k"

def get_smart_scale_filter(input_width: int, input_height: int, target_resolution: str) -> Optional[str]:
    resolution_bounds = {
        "480p": (854, 480), "720p": (1280, 720), "1080p": (1920, 1080),
        "1440p": (2560, 1440), "4k": (3840, 2160)
    }
    if target_resolution not in resolution_bounds:
        return None
    target_width, target_height = resolution_bounds[target_resolution]
    input_aspect = input_width / input_height
    target_aspect = target_width / target_height
    if input_aspect > target_aspect:
        return f"scale={target_width}:-2:flags=lanczos"
    else:
        return f"scale=-2:{target_height}:flags=lanczos"

def determine_audio_settings(audio_codec: str, container: str, input_channels: int) -> Tuple[str, int, str]:
    if audio_codec == "copy":
        return ("copy", input_channels, None)
    max_channels = MULTICHANNEL_SUPPORT.get(container, {}).get(audio_codec, 2)
    if max_channels is None:
        max_channels = 8
    output_channels = 2 if input_channels == 1 else min(input_channels, max_channels)
    if output_channels == 1: bitrate = "96k"
    elif output_channels == 2: bitrate = "128k"
    elif output_channels <= 6: bitrate = "320k"
    else: bitrate = "448k"
    return (audio_codec, output_channels, bitrate)

def get_best_audio_fallback(container: str) -> str:
    """Get the best audio codec fallback for a container."""
    fallback_priority = {
        "mp4": "aac",      # MP4 -> AAC (native support)
        "mkv": "opus",     # MKV -> Opus (best quality/size)
        "webm": "opus",    # WebM -> Opus (required)
        "avi": "mp3",      # AVI -> MP3 (legacy compatibility)
        "mov": "aac"       # MOV -> AAC (Apple standard)
    }
    return fallback_priority.get(container, "aac")

def parse_ffmpeg_progress(line: str, duration: float) -> int:
    """Parse FFmpeg output to calculate progress percentage"""
    # Improved regex to handle out_time= and more decimal places
    time_match = re.search(r'(?:out_)?time=(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)', line)
    if time_match and duration > 0:
        hours, minutes, seconds = map(float, time_match.groups())
        current_time = hours * 3600 + minutes * 60 + seconds
        progress = int((current_time / duration) * 100)
        return min(progress, 99)
    return 0

def handle_partial_file(output_path: Path, suffix: str):
    """Rename partial file if it exists"""
    if output_path.exists():
        new_path = output_path.parent / f"{output_path.stem}{suffix}{output_path.suffix}"
        if new_path.exists():
            # Add counter if already exists
            counter = 1
            while True:
                candidate = output_path.parent / f"{output_path.stem}{suffix}_{counter}{output_path.suffix}"
                if not candidate.exists():
                    new_path = candidate
                    break
                counter += 1
        output_path.rename(new_path)

# --- Main Transcoding Function ---

def transcode_video(job_id: str, input_path: str, options: TranscodingOptions):
    """
    Transcode video to specified format using FFmpeg with enhanced options.
    Updates job progress in real-time.
    """
    
    # Stage 1: Transcode to temp folder using UUID and correct extension
    container_ext = CONTAINERS[options.container.value]
    temp_path = get_temp_path(job_id, container_ext)

    try:
        job_manager.update_job(job_id, status="processing", progress=0)
        
        # Get original filename from job manager
        job = job_manager.get_job(job_id)
        original_filename = job.get("filename", "video") if job else "video"

        video_info = get_video_info(input_path)
        duration = get_video_duration(video_info)
        width, height = get_video_resolution(video_info)
        input_channels = get_audio_channels(video_info)

        # Resolve options
        video_codec = VIDEO_CODECS[options.video_codec.value]
        container = CONTAINERS[options.container.value]

        # Handle resolution
        if options.resolution == "default":
            resolution_filter = None
        elif options.resolution == "auto":
            nearest = get_nearest_standard_resolution(width, height)
            resolution_filter = get_smart_scale_filter(width, height, nearest)
        else:
            resolution_filter = get_smart_scale_filter(width, height, options.resolution.value)

        # Quality (CRF)
        crf_value = options.crf

        # Sharpening
        sharpening_filter = SHARPENING_FILTERS.get(options.sharpening.value)

        # Audio
        original_audio_codec_name = get_original_audio_codec(video_info)
        selected_audio_codec_option = options.audio_codec.value
        
        # Audio Logic
        if selected_audio_codec_option == "default":
            resolved_audio_codec_key = "aac"
        else:
            resolved_audio_codec_key = selected_audio_codec_option

        if resolved_audio_codec_key == "copy":
            if original_audio_codec_name:
                original_codec_frontend_key = FFMPEG_TO_FRONTEND_AUDIO.get(
                    original_audio_codec_name.lower()
                )
                compatible_audio = CONTAINER_CODEC_COMPATIBILITY.get(container, {}).get("audio", [])
                
                if original_codec_frontend_key and original_codec_frontend_key in compatible_audio:
                     # Audio matches container
                     pass
                else:
                    fallback = get_best_audio_fallback(container)
                    resolved_audio_codec_key = fallback
            else:
                 resolved_audio_codec_key = "aac"

        audio_codec, output_channels, audio_bitrate = determine_audio_settings(
            resolved_audio_codec_key, container, input_channels
        )
        audio_codec_real = AUDIO_CODECS.get(audio_codec, "aac") if audio_codec != "copy" else "copy"

        # Build FFmpeg command
        cmd = [settings.FFMPEG_PATH, "-i", input_path]
        
        filters = []
        if resolution_filter: filters.append(resolution_filter)
        if sharpening_filter: filters.append(sharpening_filter)
        if filters: cmd.extend(["-vf", ",".join(filters)])

        # Video codec settings
        cmd.extend(["-c:v", video_codec])
        cpu_count = os.cpu_count() or 4
        
        if video_codec in ["libx264", "libx265"]:
            cmd.extend(["-crf", str(crf_value), "-preset", "medium", "-threads", str(cpu_count)])
        elif video_codec == "libaom-av1":
            cpu_used = 6 if cpu_count >= 8 else 7
            cmd.extend(["-crf", str(crf_value), "-b:v", "0", "-cpu-used", str(cpu_used), "-row-mt", "1", "-tiles", "2x2", "-threads", str(cpu_count)])
        elif video_codec == "libvpx-vp9":
            cpu_used = 2 if cpu_count >= 8 else 3
            cmd.extend(["-crf", str(crf_value), "-b:v", "0", "-cpu-used", str(cpu_used), "-row-mt", "1", "-threads", str(cpu_count)])

        if video_codec == "libx264":
            cmd.extend(["-profile:v", "high", "-level", "4.1"])
        cmd.extend(["-pix_fmt", "yuv420p"])
        if container == "mp4":
            cmd.extend(["-movflags", "+faststart"])

        # Audio codec settings
        cmd.extend(["-c:a", audio_codec_real])
        if audio_codec_real != "copy":
            if audio_bitrate: cmd.extend(["-b:a", audio_bitrate])
            cmd.extend(["-ac", str(output_channels)])
            if audio_codec_real == "aac": cmd.extend(["-ar", "48000"])
            elif audio_codec_real == "libmp3lame": cmd.extend(["-ar", "44100"])

        cmd.extend(["-progress", "pipe:1", "-y", str(temp_path)])
        
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            encoding="utf-8", bufsize=1
        )
        
        job_manager.register_process(job_id, process)

        recent_logs = []
        try:
            for line in process.stdout:
                line_str = line.strip()
                if line_str:
                    recent_logs.append(line_str)
                    if len(recent_logs) > 30:
                        recent_logs.pop(0)

                if duration > 0:
                    progress = parse_ffmpeg_progress(line, duration)
                    if progress > job_manager.get_job(job_id).get("progress", 0):
                        job_manager.update_job(job_id, progress=progress)
        finally:
            job_manager.unregister_process(job_id)

        process.wait()

        if process.returncode == 0 and os.path.exists(temp_path):
            # Stage 2: Move to outputs with original name and collision check
            final_output_path = get_unique_output_path(original_filename, container_ext)
            move_temp_to_output(temp_path, final_output_path)
            
            file_size = get_file_size_mb(str(final_output_path))
            job_manager.complete_job(
                job_id, output_path=str(final_output_path), file_size_mb=file_size
            )
            print(f"Transcoding completed for job {job_id}. Saved to: {final_output_path}")
        else:
            job = job_manager.get_job(job_id)
            if job and job.get("status") == "cancelled":
                handle_partial_file(temp_path, "_cancelled")
                print(f"Transcoding cancelled for job {job_id}")
            else:
                error_tail = "\n".join(recent_logs[-10:]) if recent_logs else "No logs captured"
                error_log = f"FFmpeg failed (Code {process.returncode}).\nLast logs:\n{error_tail}"
                job_manager.fail_job(job_id, error_log)
                print(f"Transcoding failed for job {job_id}. Return code: {process.returncode}")
                print(f"FFmpeg Error Output:\n{error_tail}")

    except Exception as e:
        job_manager.fail_job(job_id, f"Service error: {str(e)}")
        print(f"Transcoding error for job {job_id}: {e}")
