"""
Settings Manager for Docker deployment.
Adapted from desktop version, removing PyInstaller-specific logic.
"""

import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import platform

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Singleton settings manager for Docker deployment.
    Maintains compatibility with desktop app settings structure.
    """
    
    _instance = None
    
    # Default settings - matching original base code
    _default_settings = {
        # Download settings
        "download_speed": "5M",
        "enable_download_archive": False,
        "stream_and_merge_format": "bestvideo+bestaudio/best-mkv",
        "audio_format": "m4a",
        "embed_thumbnail_in_audio": "Yes",
        "auto_update": True,
        "gui_theme": "Default",
        "platform_specific_download_folders": True,
        "multisession_queue_download_support": True,
        "track_failed_url": True,
        
        # Path settings (will be overridden with Docker paths)
        "download_folder": "/storage/downloads",
        "temp_folder": "/storage/downloads/temp",
        "bin_folder": "/storage/bin",
        "data_folder": "/storage/data",
        "docs_folder": "/storage/docs",
        
        # Cookies settings
        "cookies_path": "",
        "enable_cookies_from_browser": False,
        "cookies_browser": "",
        "cookies_browser_profile": "",
        
        # Spotify settings
        "spotify_client_id": "",
        "spotify_client_secret": "",
        "enable_spotify_playlist": False,
        
        # Tool versions/Tracking
        "last_app_update_check": 0,
        "last_ytdlp_update_check": "",
        "last_spotdl_update_check": "",
        "last_deno_update_check": "",
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._callbacks: List[callable] = []
        self._initialize()
    
    def _is_running_in_docker(self) -> bool:
        """Detect if we're running inside a Docker container."""
        # Check for .dockerenv file
        if Path("/.dockerenv").exists():
            return True
        # Check for docker in cgroup
        try:
            with open("/proc/1/cgroup", "r") as f:
                return "docker" in f.read()
        except (FileNotFoundError, PermissionError):
            pass
        # Check if /app directory exists (our Docker app directory)
        if Path("/app").exists() and Path("/storage/downloads").exists():
            return True
        return False
    
    def _initialize(self):
        """Initialize settings with environment-appropriate paths."""
        in_docker = self._is_running_in_docker()
        
        if in_docker:
            # Docker environment paths
            self._data_dir = Path(os.environ.get("APP_DATA_DIR", "/storage/data"))
            self._download_dir = Path(os.environ.get("DOWNLOAD_DIR", "/storage/downloads"))
            self._temp_dir = self._download_dir / "temp"
            self._bin_dir = Path(os.environ.get("BIN_DIR", "/storage/bin"))
            self._docs_dir = Path(os.environ.get("DOCS_DIR", "/storage/docs"))
        else:
            # Local development paths (relative to project)
            project_root = Path(__file__).parent.parent.parent
            self._data_dir = Path(os.environ.get("APP_DATA_DIR", project_root / "storage" / "data"))
            self._download_dir = Path(os.environ.get("DOWNLOAD_DIR", project_root / "storage" / "downloads"))
            self._temp_dir = self._download_dir / "temp"
            self._bin_dir = Path(os.environ.get("BIN_DIR", project_root / "storage" / "bin"))
            self._docs_dir = Path(os.environ.get("DOCS_DIR", project_root / "storage" / "docs"))
            logger.info(f"Running in local development mode. Data dir: {self._data_dir}")
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Load or create settings
        self._settings = self._load_settings()
        
        # Apply Docker path defaults
        self._apply_docker_paths()
        
        logger.info(f"Settings initialized from {self._get_settings_path()}")
    
    def _ensure_directories(self):
        """Ensure all necessary directories exist."""
        # Core directories
        for directory in [self._data_dir, self._download_dir, self._temp_dir, self._bin_dir, self._docs_dir]:
            if os.path.exists(directory):
                if not os.path.isdir(directory):
                    raise FileExistsError(f"Path exists but is not a directory: {directory}")
            else:
                os.makedirs(directory, exist_ok=True)

        # Download subdirectories (matching original code)
        audio_dir = self._download_dir / "Audio"
        video_dir = self._download_dir / "Video"

        if os.path.exists(audio_dir):
            if not os.path.isdir(audio_dir):
                raise FileExistsError(f"Path exists but is not a directory: {audio_dir}")
        else:
            os.makedirs(audio_dir, exist_ok=True)

        if os.path.exists(video_dir):
            if not os.path.isdir(video_dir):
                raise FileExistsError(f"Path exists but is not a directory: {video_dir}")
        else:
            os.makedirs(video_dir, exist_ok=True)
    
    def _get_settings_path(self) -> Path:
        """Get path to settings file."""
        return self._data_dir / "settings.json"
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file or return defaults."""
        settings_path = self._get_settings_path()
        
        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    merged = self._default_settings.copy()
                    merged.update(loaded)
                    return merged
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading settings: {e}")
        
        return self._default_settings.copy()
    
    def _apply_docker_paths(self):
        """Apply Docker-specific path defaults."""
        self._settings["download_folder"] = str(self._download_dir)
        self._settings["temp_folder"] = str(self._temp_dir)
        self._settings["bin_folder"] = str(self._bin_dir)
        self._settings["data_folder"] = str(self._data_dir)
        self._settings["docs_folder"] = str(self._docs_dir)
    
    def save_settings(self, settings: Dict[str, Any] = None):
        """Save settings to file with auto-normalization for paths."""
        if settings:
            # Normalize path-related keys before updating
            path_keys = {"download_folder", "temp_folder", "bin_folder", "data_folder", "cookies_path", "cookies_browser_profile"}
            for key, value in settings.items():
                if key in path_keys or key.endswith(("_folder", "_path", "_dir")):
                    if isinstance(value, str):
                        settings[key] = self.normalize_path(value)
            
            self._settings.update(settings)
        
        settings_path = self._get_settings_path()
        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2)
            self._notify_callbacks()
            logger.info("Settings saved successfully")
        except IOError as e:
            logger.error(f"Error saving settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = True):
        """Set a setting value with auto-normalization for paths."""
        path_keys = {"download_folder", "temp_folder", "bin_folder", "data_folder", "cookies_path", "cookies_browser_profile"}
        if key in path_keys or key.endswith(("_folder", "_path", "_dir")):
            if isinstance(value, str):
                value = self.normalize_path(value)
        
        self._settings[key] = value
            
        if save:
            self.save_settings()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all current settings."""
        return self._settings.copy()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self._settings = self._default_settings.copy()
        self._apply_docker_paths()
        self.save_settings()
    
    def get_download_folder(self) -> Path:
        """Get the download folder path."""
        return Path(self._settings.get("download_folder", "/storage/downloads"))
    
    def get_temp_folder(self) -> Path:
        """Get the temp folder path."""
        return Path(self._settings.get("temp_folder", "/storage/downloads/temp"))
    
    def get_bin_folder(self) -> Path:
        """Get the bin folder path."""
        return Path(self._settings.get("bin_folder", "/app/bin"))
    
    def get_data_folder(self) -> Path:
        """Get the data folder path."""
        return Path(self._settings.get("data_folder", "/storage/data"))
    
    def get_docs_folder(self) -> Path:
        """Get the docs folder path."""
        return Path(self._settings.get("docs_folder", "/storage/docs"))
    
    def get_cookies_cmd(self) -> List[str]:
        """Get cookies command arguments for yt-dlp."""
        cookies_cmd = []
        cookies_path = self.get("cookies_path")
        
        if cookies_path and os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
            cookies_cmd.extend(["--cookies", cookies_path])
        elif self.get("enable_cookies_from_browser"):
            cookies_browser = self.get("cookies_browser")
            cookies_browser_profile = self.get("cookies_browser_profile")
            if cookies_browser_profile:
                cookies_browser += f":{cookies_browser_profile}"
            cookies_cmd.extend(["--cookies-from-browser", cookies_browser])
            
        return cookies_cmd
    
    def get_spotify_credentials(self) -> Optional[Dict[str, str]]:
        """Get Spotify API credentials if configured."""
        # Always return credentials if they exist in this version
        client_id = self._settings.get("spotify_client_id", "")
        client_secret = self._settings.get("spotify_client_secret", "")
        if client_id and client_secret:
            return {
                "client_id": client_id,
                "client_secret": client_secret
            }
        return None
    
    def normalize_path(self, path: str) -> str:
        """
        Normalize path for cross-platform compatibility.
        Handles Windows paths (E:\\test, e:/test) and Linux paths.
        Specifically handles WSL mapping (E:/ -> /mnt/e/).
        """
        if not path:
            return path
            
        # Strip surrounding quotes if present
        path = path.strip().strip('"').strip("'")
        
        # Convert backslashes to forward slashes
        path = path.replace("\\", "/")
        
        # Handle Windows drive letters
        match = re.match(r'^([a-zA-Z]):/?(.*)$', path)
        if match:
            drive = match.group(1).lower()
            rest = match.group(2)
            
            # Detect if we should use /mnt/ style (WSL or typical Docker mount)
            is_linux = platform.system() == "Linux"
            if is_linux:
                return f"/mnt/{drive}/{rest}" if rest else f"/mnt/{drive}"
            else:
                # Local Windows: ensure drive is capitalized and use forward slashes
                return f"{drive.upper()}:/{rest}" if rest else f"{drive.upper()}:/"
        
        # Handle WSL paths on native Windows if needed
        if platform.system() == "Windows" and path.startswith("/mnt/"):
            parts = path.split("/")
            if len(parts) >= 3 and len(parts[2]) == 1: # /mnt/e/
                drive = parts[2]
                rest = "/".join(parts[3:])
                return f"{drive.upper()}:/{rest}" if rest else f"{drive.upper()}:/"

        return path
    
    def register_callback(self, callback: callable):
        """Register a callback for settings changes."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: callable):
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """Notify all registered callbacks about settings changes."""
        for callback in self._callbacks:
            try:
                callback(self._settings)
            except Exception as e:
                logger.error(f"Error in settings callback: {e}")
    
    def is_healthy(self) -> bool:
        """Check if settings are in good state."""
        try:
            return (
                self._data_dir.exists() and
                self._download_dir.exists() and
                bool(self._settings)
            )
        except Exception:
            return False


# Singleton instance
settings_manager = SettingsManager()
