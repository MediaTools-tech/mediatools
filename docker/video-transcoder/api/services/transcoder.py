import subprocess
import re
import os
import json
from pathlib import Path
from typing import Dict, Tuple, Optional

from api.config import settings
from api.services.storage import get_output_path, get_file_size_mb
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
    "default": "aac",
    "copy": "copy",
    "aac": "aac",
    "mp3": "libmp3lame",
    "opus": "libopus",
    "vorbis": "libvorbis",
    "ac3": "ac3",
    "flac": "flac"
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
        "audio": ["aac", "mp3", "ac3", "copy"]
    },
    "mkv": {
        "video": ["libx264", "libx265", "libvpx-vp9", "libaom-av1"],
        "audio": ["aac", "mp3", "ac3", "opus", "flac", "vorbis", "copy"]
    },
    "avi": {
        "video": ["libx264"],
        "audio": ["mp3", "ac3", "copy"]
    },
    "webm": {
        "video": ["libvpx-vp9", "libaom-av1"],
        "audio": ["opus", "vorbis", "copy"]
    },
    "mov": {
        "video": ["libx264", "libx265"],
        "audio": ["aac", "mp3", "ac3", "copy"]
    }
}


def get_video_info(input_path: str) -> Optional[Dict]:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(input_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
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

def parse_ffmpeg_progress(line: str, duration: float) -> int:
    """Parse FFmpeg output to calculate progress percentage"""
    time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
    if time_match and duration > 0:
        hours, minutes, seconds = map(float, time_match.groups())
        current_time = hours * 3600 + minutes * 60 + seconds
        progress = int((current_time / duration) * 100)
        return min(progress, 99)
    return 0

# --- Main Transcoding Function ---

def transcode_video(job_id: str, input_path: str, options: TranscodingOptions):
    """
    Transcode video to specified format using FFmpeg with enhanced options.
    Updates job progress in real-time.
    """
    print(f"Starting transcoding for job {job_id} with options: {options.dict()}")
    
    # Use job_id for the output filename, but the container from options
    output_path = get_output_path(job_id).with_suffix(f".{CONTAINERS[options.container]}")

    try:
        job_manager.update_job(job_id, status="processing", progress=0)

        video_info = get_video_info(input_path)
        duration = get_video_duration(video_info)
        width, height = get_video_resolution(video_info)
        input_channels = get_audio_channels(video_info)

        # Resolve options
        video_codec = VIDEO_CODECS[options.video_codec]
        container = CONTAINERS[options.container]

        # Handle resolution
        if options.resolution == "default":
            resolution_filter = None
        elif options.resolution == "auto":
            nearest = get_nearest_standard_resolution(width, height)
            resolution_filter = get_smart_scale_filter(width, height, nearest)
        else:
            resolution_filter = get_smart_scale_filter(width, height, options.resolution)

        # Sharpening
        sharpening_filter = SHARPENING_FILTERS.get(options.sharpening)

        # Audio
        original_audio_codec_name = get_original_audio_codec(video_info)
        selected_audio_codec_option = options.audio_codec # e.g., "default", "copy", "aac", "flac"
        
        # Resolve "default" audio codec to "aac"
        if selected_audio_codec_option == "default":
            resolved_audio_codec_key = "aac"
        else:
            resolved_audio_codec_key = selected_audio_codec_option

        # Handle "copy" option intelligently
        if resolved_audio_codec_key == "copy":
            if original_audio_codec_name:
                # Try to map FFmpeg's original audio codec name to our frontend key
                original_codec_frontend_key = None
                for key, value in AUDIO_CODECS.items():
                    if value == original_audio_codec_name:
                        original_codec_frontend_key = key
                        break

                compatible_audio_options_for_container = CONTAINER_CODEC_COMPATIBILITY.get(container, {}).get("audio", [])

                if original_codec_frontend_key and original_codec_frontend_key in compatible_audio_options_for_container:
                    # Original codec is compatible, so we can copy
                    print(f"Original audio codec '{original_audio_codec_name}' is compatible with '{container}'. Proceeding with copy.")
                else:
                    # Original codec not compatible, fallback to a transcode option
                    fallback_codec_key = next(
                        (ac for ac in compatible_audio_options_for_container if ac not in ["copy", "default"]),
                        "aac" # Fallback to aac if no other suitable codec found
                    )
                    resolved_audio_codec_key = fallback_codec_key
                    print(f"Original audio codec '{original_audio_codec_name}' not compatible with '{container}'. Falling back to '{resolved_audio_codec_key}'.")
            else:
                # No original audio track found for copying. Fallback to default (aac).
                resolved_audio_codec_key = "aac"
                print(f"No original audio track found for copying. Falling back to 'aac'.")

        # Determine audio settings based on the final resolved_audio_codec_key
        # The determine_audio_settings function will handle "copy" if that's the resolved key.
        audio_codec, output_channels, audio_bitrate = determine_audio_settings(
            resolved_audio_codec_key, container, input_channels
        )
        # audio_codec_real is the actual FFmpeg codec string
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
            cmd.extend(["-crf", str(options.crf), "-preset", "medium", "-threads", str(cpu_count)])
        elif video_codec == "libaom-av1":
            cpu_used = 6 if cpu_count >= 8 else 7
            cmd.extend(["-crf", str(options.crf), "-b:v", "0", "-cpu-used", str(cpu_used), "-row-mt", "1", "-tiles", "2x2", "-threads", str(cpu_count)])
        elif video_codec == "libvpx-vp9":
            cpu_used = 2 if cpu_count >= 8 else 3
            cmd.extend(["-crf", str(options.crf), "-b:v", "0", "-cpu-used", str(cpu_used), "-row-mt", "1", "-threads", str(cpu_count)])

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

        cmd.extend(["-progress", "pipe:1", "-y", str(output_path)])
        
        print(f"Executing FFmpeg command: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, bufsize=1
        )

        for line in process.stdout:
            print(line.strip()) # Log ffmpeg output
            if duration > 0:
                progress = parse_ffmpeg_progress(line, duration)
                if progress > job_manager.get_job(job_id).get("progress", 0):
                    job_manager.update_job(job_id, progress=progress)

        process.wait()

        if process.returncode == 0 and os.path.exists(output_path):
            file_size = get_file_size_mb(output_path)
            job_manager.complete_job(
                job_id, output_path=str(output_path), file_size_mb=file_size
            )
            print(f"Transcoding completed for job {job_id}")
        else:
            # Try to get error from ffmpeg output
            error_log = "FFmpeg transcoding failed. Return code: " + str(process.returncode)
            job_manager.fail_job(job_id, error_log)
            print(f"Transcoding failed for job {job_id}")

    except Exception as e:
        job_manager.fail_job(job_id, str(e))
        print(f"Transcoding error for job {job_id}: {e}")
