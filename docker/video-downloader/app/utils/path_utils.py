"""
Path utilities for cross-platform path handling.
"""

import os
import re
from pathlib import Path
from typing import Optional
import platform

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"


def normalize_path(path: str) -> str:
    """
    Normalize path for cross-platform compatibility.
    Handles Windows paths (E:\\test, e:/test) and Linux paths.
    """
    if not path:
        return path
    
    # Convert backslashes to forward slashes
    path = path.replace("\\", "/")
    
    # Remove trailing slashes
    path = path.rstrip("/")
    
    return path


def ensure_directory(path: Path) -> bool:
    """Ensure a directory exists, create if necessary."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def safe_filename(filename: str, max_length: int = 200) -> str:
    """
    Create a safe filename by removing/replacing invalid characters.
    """
    if not filename:
        return "unnamed"
    
    # Replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Trim whitespace
    filename = filename.strip()
    
    # Truncate if too long
    if len(filename) > max_length:
        # Keep extension if present
        name, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext)
        filename = name[:max_name_length] + ext
    
    return filename or "unnamed"


def get_unique_filename(directory: Path, filename: str) -> Path:
    """
    Get a unique filename in the given directory.
    If file exists, append (1), (2), etc.
    """
    filepath = directory / filename
    
    if not filepath.exists():
        return filepath
    
    name, ext = os.path.splitext(filename)
    counter = 1
    
    while True:
        new_filename = f"{name} ({counter}){ext}"
        new_filepath = directory / new_filename
        
        if not new_filepath.exists():
            return new_filepath
        
        counter += 1
        
        # Safety limit
        if counter > 1000:
            import uuid
            return directory / f"{name}_{uuid.uuid4().hex[:8]}{ext}"


def get_file_size_formatted(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def is_media_file(filepath: Path) -> bool:
    """Check if a file is a media file based on extension."""
    media_extensions = {
        # Video
        '.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.wmv', '.m4v',
        # Audio
        '.mp3', '.m4a', '.opus', '.ogg', '.flac', '.wav', '.aac', '.wma'
    }
    return filepath.suffix.lower() in media_extensions


def is_video_file(filepath: Path) -> bool:
    """Check if a file is a video file."""
    video_extensions = {'.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.wmv', '.m4v'}
    return filepath.suffix.lower() in video_extensions


def is_audio_file(filepath: Path) -> bool:
    """Check if a file is an audio file."""
    audio_extensions = {'.mp3', '.m4a', '.opus', '.ogg', '.flac', '.wav', '.aac', '.wma'}
    return filepath.suffix.lower() in audio_extensions


def is_partial_download(filepath: Path) -> bool:
    """Check if a file is a partial/incomplete download."""
    partial_patterns = ['.part', '.ytdl', '.temp', '.tmp', '.download']
    name_lower = filepath.name.lower()
    return any(pattern in name_lower for pattern in partial_patterns)


def get_temp_path(base_dir: Path, prefix: str = "download_") -> Path:
    """Get a temporary file path in the given directory."""
    import uuid
    return base_dir / f"{prefix}{uuid.uuid4().hex[:12]}"


def windows_to_wsl_path(windows_path: str) -> str:
    """
    Convert Windows path to WSL path.
    E:\\test -> /mnt/e/test
    """
    # Match Windows drive letter pattern
    match = re.match(r'^([a-zA-Z]):[\\/]?(.*)$', windows_path)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace('\\', '/')
        return f"/mnt/{drive}/{rest}"
    return windows_path


def wsl_to_windows_path(wsl_path: str) -> str:
    """
    Convert WSL path to Windows path.
    /mnt/e/test -> E:\\test
    """
    match = re.match(r'^/mnt/([a-zA-Z])/(.*)$', wsl_path)
    if match:
        drive = match.group(1).upper()
        rest = match.group(2).replace('/', '\\')
        return f"{drive}:\\{rest}"
    return wsl_path
