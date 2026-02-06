import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import logging

class SettingsManager:
    _instance = None

    _default_settings = {
        "bin_dir": "",
        "downloads_dir": "", # Default output dir
        "data_dir": "",
        "queue_file": "",
        "gui_theme": "Default",
        "auto_update": True,
        "multi_session_enabled": True,
        "use_defaults": True,
        "last_ffmpeg_update_check": 0,
        "last_container": "mp4",
        "last_video_codec": "h264",
        "last_audio_codec": "aac",
        "last_resolution": "default",
        "crf": 23,
        "last_app_update_check": 0
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.dynamic_paths = self._calculate_dynamic_paths()
        self.settings_file = self._get_settings_path()
        self.current_settings = self._load_settings()
        
        # Ensure path defaults
        for key, default_path in self.dynamic_paths.items():
            if not self.current_settings.get(key):
                self.current_settings[key] = default_path
        
        self._extract_bundled_resources() # Copy bundled stuff to storage
        self.save_settings()
        self._ensure_directories()

    def _extract_bundled_resources(self):
        """Copy bundled bin/assets to the storage directory on first run"""
        if not getattr(sys, "frozen", False):
            return
            
        import shutil
        bundle_root = Path(sys._MEIPASS)
        storage_root = Path(self.get("base_dir"))
        
        # We only want to copy if the destination doesn't exist or is empty
        for folder in ["bin", "data", "assets"]:
            src = bundle_root / folder
            if not src.exists(): # Try _internal fallback for modern PyInstaller
                src = bundle_root / "_internal" / folder
                
            if src.exists():
                dst = storage_root / folder
                if not dst.exists() or not os.listdir(str(dst)):
                    os.makedirs(str(dst), exist_ok=True)
                    for item in os.listdir(str(src)):
                        s = src / item
                        d = dst / item
                        if s.is_file():
                            shutil.copy2(str(s), str(d))

    def _get_bundle_resource(self, relative_path: str) -> Path:
        """Helper to find bundled resources in either the root or _internal folder"""
        if getattr(sys, "frozen", False):
            root = Path(sys._MEIPASS)
            # Case 1: Root (onefile or old onedir)
            path = root / relative_path
            if path.exists():
                return path
            # Case 2: Inside _internal (modern onedir)
            internal_path = root / "_internal" / relative_path
            if internal_path.exists():
                return internal_path
            return path
        else:
            # Dev mode
            return Path(__file__).parent.parent / relative_path

    def _calculate_dynamic_paths(self):
        base_dir = self.get_persistent_data_dir() if self.is_onefile_build() else self.get_app_root()
        
        downloads_dir = base_dir / "transcoded"
        data_dir = base_dir / "data"
        bin_dir = base_dir / "bin"
        
        return {
            "base_dir": str(base_dir),
            "downloads_dir": str(downloads_dir),
            "data_dir": str(data_dir),
            "bin_dir": str(bin_dir),
            "queue_file": str(data_dir / "queue.txt"),
        }

    def get_app_root(self):
        """Get the application root directory"""
        if getattr(sys, "frozen", False):
            # PyInstaller build (onefile or onedir)
            exe_dir = Path(sys.executable).parent
            if (exe_dir / "_internal").exists():
                return exe_dir / "_internal"
            else:
                return Path(sys._MEIPASS)
        else:
            # Development
            return Path(__file__).parent.parent

    def get_persistent_data_dir(self):
        app_name = "Video Transcoder"
        if sys.platform == "win32":
            data_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "MediaTools" / app_name
        elif sys.platform == "darwin":
            data_dir = Path.home() / "Library" / "Application Support" / "MediaTools" / app_name
        else:
            data_dir = Path.home() / ".local" / "share" / "MediaTools" / app_name
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def is_onefile_build(self):
        """Check if running as PyInstaller onefile build"""
        return (
            getattr(sys, "frozen", False)
            and hasattr(sys, "_MEIPASS")
            and not os.path.exists(
                os.path.join(os.path.dirname(sys.executable), "_internal")
            )
        )

    def _get_settings_path(self):
        base_dir = self.get_persistent_data_dir() if self.is_onefile_build() else self.get_app_root()
        return base_dir / "data" / "settings.json"

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings and filter out irrelevant/junk keys"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    user_settings = json.load(f)
                
                # Filter to only keep transcoder-relevant keys
                valid_keys = set(self._default_settings.keys()) | set(self.dynamic_paths.keys()) | {"base_dir"}
                filtered = {k: v for k, v in user_settings.items() if k in valid_keys}
                
                merged = self._default_settings.copy()
                merged.update(filtered)
                return merged
        except Exception as e:
            print(f"Error loading settings: {e}")
        return self._default_settings.copy()

    def save_settings(self):
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.current_settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.current_settings.get(key, default)

    def set(self, key: str, value: Any):
        self.current_settings[key] = value
        self.save_settings()

    def _ensure_directories(self):
        for path_key in ["downloads_dir", "data_dir", "bin_dir"]:
            path = self.get(path_key)
            if path:
                os.makedirs(path, exist_ok=True)
