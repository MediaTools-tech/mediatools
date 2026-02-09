import subprocess
import re
import os
import json
import platform
import threading
from pathlib import Path
from typing import Dict, Tuple, Optional, Callable, Any

# --- Constants & Presets ---

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

class TranscoderEngine:
    def __init__(self, ffmpeg_path: str, ffprobe_path: str):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.active_process = None
        self._lock = threading.Lock()

    def get_video_info(self, input_path: str) -> Optional[Dict]:
        """Get video metadata using ffprobe."""
        cmd = [
            self.ffprobe_path, "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", str(input_path)
        ]
        try:
            # Creation flags for Windows to hide console window
            process_kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "universal_newlines": True
            }
            if platform.system() == "Windows":
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                
            with self._lock:
                self.active_process = subprocess.Popen(cmd, **process_kwargs)
            
            stdout, stderr = self.active_process.communicate()
            
            if self.active_process.returncode != 0:
                return None
                
            return json.loads(stdout)
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            print(f"Error getting video info: {e}")
            return None
        finally:
            with self._lock:
                self.active_process = None

    def get_video_duration(self, video_info: Dict) -> float:
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

    def get_audio_channels(self, video_info: Dict) -> int:
        if not video_info:
            return 2
        for stream in video_info.get("streams", []):
            if stream.get("codec_type") == "audio":
                return stream.get("channels", 2)
        return 2

    def get_original_audio_codec(self, video_info: Dict) -> Optional[str]:
        """Extract original audio codec from video info."""
        if not video_info:
            return None
        for stream in video_info.get("streams", []):
            if stream.get("codec_type") == "audio":
                return stream.get("codec_name")
        return None

    def get_video_resolution(self, video_info: Dict) -> Tuple[int, int]:
        if not video_info:
            return (1920, 1080)
        for stream in video_info.get("streams", []):
            if stream.get("codec_type") == "video":
                width = stream.get("width", 1920)
                height = stream.get("height", 1080)
                return (width, height)
        return (1920, 1080)

    def get_nearest_standard_resolution(self, width: int, height: int) -> str:
        if height <= 480: return "480p"
        elif height <= 720: return "720p"
        elif height <= 1080: return "1080p"
        elif height <= 1440: return "1440p"
        else: return "4k"

    def get_smart_scale_filter(self, input_width: int, input_height: int, target_resolution: str) -> Optional[str]:
        resolution_bounds = {
            "480p": (854, 480), "720p": (1280, 720), "1080p": (1920, 1080),
            "1440p": (2560, 1440), "4k": (3840, 2160)
        }
        if target_resolution not in resolution_bounds:
            return None
        target_width, target_height = resolution_bounds[target_resolution]
        
        # If input is smaller than target, don't upscale? Or do we? 
        # The logic below scales down if input is larger. 
        # If input is smaller, it might upscale. Let's keep original logic.
        
        input_aspect = input_width / input_height
        target_aspect = target_width / target_height
        
        if input_aspect > target_aspect:
             # Input is wider than target aspect (e.g. 21:9 input vs 16:9 target)
             # Resize based on width? No, usually we limit by the smaller dimension to fit in the box.
             # Wait, the logic: "scale=target_width:-2" sets width to targetW, and height auto-calculated (maintaining aspect).
             return f"scale={target_width}:-2:flags=lanczos"
        else:
             # Input is taller/narrower (e.g. 4:3 input vs 16:9 target)
             # Resize based on height
             return f"scale=-2:{target_height}:flags=lanczos"

    def get_best_audio_fallback(self, container: str) -> str:
        """Get the best audio codec fallback for a container."""
        fallback_priority = {
            "mp4": "aac",      # MP4 -> AAC (native support)
            "mkv": "opus",     # MKV -> Opus (best quality/size)
            "webm": "opus",    # WebM -> Opus (required)
            "avi": "mp3",      # AVI -> MP3 (legacy compatibility)
            "mov": "aac"       # MOV -> AAC (Apple standard)
        }
        return fallback_priority.get(container, "aac")

    def determine_audio_settings(self, audio_codec: str, container: str, input_channels: int) -> Tuple[str, int, str]:
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

    def parse_ffmpeg_progress(self, line: str, duration: float) -> Optional[int]:
        """Parse FFmpeg output to calculate progress percentage"""
        # Improved regex to handle out_time= and more decimal places
        time_match = re.search(r'(?:out_)?time=(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)', line)
        if time_match and duration > 0:
            hours, minutes, seconds = map(float, time_match.groups())
            current_time = hours * 3600 + minutes * 60 + seconds
            progress = int((current_time / duration) * 100)
            return min(progress, 99)
        return None

    def transcode_video(
        self,
        input_path: str,
        output_path: str,
        options: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None,
        stop_event = None,
        pause_event = None
    ):
        """
        Transcode video to specified format using FFmpeg.
        
        options dict should contain:
        - container: str (key in CONTAINERS)
        - video_codec: str (key in VIDEO_CODECS)
        - audio_codec: str (key in AUDIO_CODECS)
        - resolution: str ("default", "auto", "1080p", etc.)
        - sharpening: str (key in SHARPENING_FILTERS)
        - crf: int (18-28 usually)
        """
        print(f"Starting transcoding: {input_path} -> {output_path}")
        
        video_info = self.get_video_info(input_path)
        if not video_info:
            raise ValueError("Could not get video info. Is the file corrupted or FFprobe missing?")
            
        duration = self.get_video_duration(video_info)
        width, height = self.get_video_resolution(video_info)
        input_channels = self.get_audio_channels(video_info)

        # Resolve options
        container_key = options.get("container", "default")
        video_codec_key = options.get("video_codec", "default")
        audio_codec_key = options.get("audio_codec", "default")
        resolution_key = options.get("resolution", "default")
        sharpening_key = options.get("sharpening", "none")
        crf = options.get("crf", 23)

        print(f"Transcoding Options Selected:")
        print(f"  - Video Codec: {video_codec_key}")
        print(f"  - Container: {container_key}")
        print(f"  - Audio Codec: {audio_codec_key}")
        print(f"  - Resolution: {resolution_key}")
        print(f"  - Sharpening: {sharpening_key}")
        print(f"  - CRF Value: {crf}")

        # Resolve keys to their actual format names for lookups
        container = CONTAINERS.get(container_key, "mp4")
        video_codec = VIDEO_CODECS.get(video_codec_key, "libx264")
        
        # Audio logic needs care with "copy"
        if audio_codec_key == "default":
            resolved_audio_codec_key = "aac"
        else:
            resolved_audio_codec_key = audio_codec_key

        # Sharpening
        sharpening_filter = SHARPENING_FILTERS.get(sharpening_key)

        # Handle resolution
        if resolution_key == "default":
            resolution_filter = None
        elif resolution_key == "auto":
            nearest = self.get_nearest_standard_resolution(width, height)
            resolution_filter = self.get_smart_scale_filter(width, height, nearest)
        else:
            resolution_filter = self.get_smart_scale_filter(width, height, resolution_key)

        # Sharpening
        sharpening_filter = SHARPENING_FILTERS.get(sharpening_key)

        # Audio
        original_audio_codec_name = self.get_original_audio_codec(video_info)
        
        # Audio Logic
        resolved_audio_codec_key = audio_codec_key
        if resolved_audio_codec_key == "default":
            resolved_audio_codec_key = "aac"
            
        if resolved_audio_codec_key == "copy":
            if original_audio_codec_name:
                # Step 1: Map FFmpeg codec name to our frontend key
                original_codec_frontend_key = FFMPEG_TO_FRONTEND_AUDIO.get(
                    original_audio_codec_name.lower()
                )
                
                # Step 2: Get compatible audio codecs for target container
                compatible_audio = CONTAINER_CODEC_COMPATIBILITY.get(container, {}).get("audio", [])
                
                if original_codec_frontend_key and original_codec_frontend_key in compatible_audio:
                     print(f"Copying audio: {original_audio_codec_name}")
                else:
                    # Incompatible or unknown, choose best fallback
                    fallback = self.get_best_audio_fallback(container)
                    reason = f"Unknown codec '{original_audio_codec_name}'" if not original_codec_frontend_key else f"Incompatible codec '{original_codec_frontend_key}'"
                    print(f"Cannot copy audio: {reason} to {container}. Falling back to {fallback}")
                    resolved_audio_codec_key = fallback
            else:
                 resolved_audio_codec_key = "aac"

        # Determine audio settings - use resolved container/codec for specs lookup
        final_audio_codec, output_channels, audio_bitrate = self.determine_audio_settings(
            resolved_audio_codec_key, container, input_channels
        )
        audio_codec_real = AUDIO_CODECS.get(final_audio_codec, "aac") if final_audio_codec != "copy" else "copy"

        # Build Command
        cmd = [self.ffmpeg_path, "-i", input_path]
        
        filters = []
        if resolution_filter: filters.append(resolution_filter)
        if sharpening_filter: filters.append(sharpening_filter)
        if filters: cmd.extend(["-vf", ",".join(filters)])
        
        # Video Codec
        cmd.extend(["-c:v", video_codec])
        cpu_count = os.cpu_count() or 4
        
        if video_codec in ["libx264", "libx265"]:
            cmd.extend(["-crf", str(crf), "-preset", "medium", "-threads", str(cpu_count)])
        elif video_codec == "libaom-av1":
            cpu_used = 6 if cpu_count >= 8 else 5
            cmd.extend(["-crf", str(crf), "-b:v", "0", "-cpu-used", str(cpu_used), "-row-mt", "1", "-tiles", "2x2", "-threads", str(cpu_count)])
        elif video_codec == "libvpx-vp9":
             cpu_used = 2 if cpu_count >= 8 else 3
             cmd.extend(["-crf", str(crf), "-b:v", "0", "-cpu-used", str(cpu_used), "-row-mt", "1", "-threads", str(cpu_count)])

        if video_codec == "libx264":
            cmd.extend(["-profile:v", "high", "-level", "4.1"])
            
        cmd.extend(["-pix_fmt", "yuv420p"])
        if container == "mp4":
            cmd.extend(["-movflags", "+faststart"])
            
        # Audio Codec
        cmd.extend(["-c:a", audio_codec_real])
        if audio_codec_real != "copy":
            if audio_bitrate: cmd.extend(["-b:a", audio_bitrate])
            cmd.extend(["-ac", str(output_channels)])
            if audio_codec_real == "aac": cmd.extend(["-ar", "48000"])
            elif audio_codec_real == "libmp3lame": cmd.extend(["-ar", "44100"])

        cmd.extend(["-progress", "pipe:1", "-y", str(output_path)])
        
        print(f"Executing FFmpeg command: {' '.join(cmd)}")
        
        # Execution
        process_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "universal_newlines": True,
            "bufsize": 1
        }
        if platform.system() == "Windows":
            process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            # No longer using startupinfo

        with self._lock:
            self.active_process = subprocess.Popen(cmd, **process_kwargs)
        
        for line in self.active_process.stdout:
            # Check stop/pause events
            if (stop_event and stop_event.is_set()) or (pause_event and pause_event.is_set()):
                self.terminate_active_process()
                print("Transcoding stopped/paused by user.")
                return

            if duration > 0:
                prog = self.parse_ffmpeg_progress(line, duration)
                if prog is not None and progress_callback:
                    progress_callback(prog, line.strip())

        self.active_process.wait()
        
        return_code = self.active_process.returncode
        with self._lock:
            self.active_process = None

        if return_code != 0:
            raise Exception(f"FFmpeg failed with return code {return_code}")

    def terminate_active_process(self):
        """Forcefully kill the currently active subprocess"""
        with self._lock:
            if self.active_process and self.active_process.poll() is None:
                try:
                    self.active_process.terminate()
                    try:
                        self.active_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.active_process.kill()
                        self.active_process.wait(timeout=2)
                except Exception as e:
                    print(f"Error killing process: {e}")
                finally:
                    self.active_process = None
            
