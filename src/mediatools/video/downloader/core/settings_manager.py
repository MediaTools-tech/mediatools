# settings_manager.py - Fixed version
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import logging
import shutil

class SettingsManager:
    _instance = None

    # Default settings - these should not be modified after initialization
    _default_settings = {
        # Download settings
        "download_speed": "5M",
        "enable_download_archive": False,
        "stream_and_merge_format": "bestvideo+bestaudio/best-mkv",
        "auto_update": True,
        "gui_theme": "Default",
        "platform_specific_download_folders": False,
        "multisession_queue_download_support": True,
        "track_failed_url": True,
        # Path settings - these will be dynamically set
        "base_dir": "",
        "downloads_dir": "",
        "data_dir": "",
        "utils_dir": "",
        "docs_dir": "",
        "bin_dir": "",
        "assets_dir": "",
        "queue_file": "",
        "queue_file_old": "",
        "failed_url_file": "",
        "failed_url_file_old": "",
        "download_archive_path": "",
        # Cookies settings
        "cookies_path": "",
        "enable_cookies_from_browser": False,
        "cookies_browser": "",
        "cookies_browser_profile": "",
        # "cookies_cmd": [],
        # "cookies_from_browser_cmd": [],
        # "supported_browsers": [
        #     "brave", "chrome", "chromium", "edge", "firefox",
        #     "opera", "safari", "vivaldi", "whale",
        # ],
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize settings with portable path calculations"""
        self.format_change_callback = None
        
        # Calculate dynamic paths
        self.dynamic_paths = self._calculate_dynamic_paths()
        
        # Load settings first
        self.settings_file = self._get_settings_path()
        self.current_settings = self._load_settings()
        self.callbacks = []

        # Only update paths that are empty (not customized by user)
        self._ensure_path_defaults()

        self._extract_bundled_resources()

        # Save any updates
        self.save_settings()
        self._ensure_directories()

    def _extract_bundled_resources(self):
        """Extract bundled resources to persistent directory on first run or update"""
        # if not getattr(sys, 'frozen', False):
        #     return  # Skip in development mode

        if not getattr(sys, 'frozen', False) or not hasattr(sys, '_MEIPASS'):
                return  # Skip in dev mode and --onedir mode

        import shutil
        
        # temp_base = Path(sys._MEIPASS)
        temp_base = None
        exe_dir = Path(sys.executable).parent
        if (exe_dir / '_internal').exists():
            temp_base = Path(sys.executable).parent
        else:
            temp_base = Path(sys._MEIPASS)
                
        persistent_base = self.get_persistent_data_dir()
        
        # Extract assets
        temp_assets = temp_base / 'assets'
        persistent_assets = persistent_base / 'assets'
        if temp_assets.exists():
            self._copy_directory_contents(temp_assets, persistent_assets)
        
        # Extract utils
        temp_utils = temp_base / 'utils'
        persistent_utils = persistent_base / 'utils'
        if temp_utils.exists():
            self._copy_directory_contents(temp_utils, persistent_utils)

        # Extract docs
        temp_docs = temp_base / 'docs'
        persistent_docs = persistent_base / 'docs'
        if temp_docs.exists():
            self._copy_directory_contents(temp_docs, persistent_docs)

    def _copy_directory_contents(self, src, dst):
        """Copy directory contents, overwriting existing files"""
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if item.is_file():
                shutil.copy2(item, dst / item.name)

    def _calculate_dynamic_paths(self):
        """Calculate dynamic paths based on current environment"""
        if self.is_onefile_build():
            base_dir = self.get_persistent_data_dir()
            print(f"Using persistent storage: {base_dir}")
        else:
            base_dir = self.get_app_root()

        downloads_dir = base_dir / "videos"
        data_dir = base_dir / "data"
        utils_dir = base_dir / "utils"
        docs_dir = base_dir / "docs"
        bin_dir = base_dir / "bin"
        assets_dir = base_dir / "assets"

        # Create directories if they don't exist
        downloads_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        bin_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)
        utils_dir.mkdir(parents=True, exist_ok=True)
        docs_dir.mkdir(parents=True, exist_ok=True)

        return {
            "base_dir": str(base_dir),
            "downloads_dir": str(downloads_dir),
            "data_dir": str(data_dir),
            "utils_dir": str(utils_dir),
            "docs_dir": str(docs_dir),
            "bin_dir": str(bin_dir),
            "assets_dir": str(assets_dir),
            "queue_file": str(data_dir / "queue.txt"),
            "queue_file_old": str(data_dir / "queue_old.txt"),
            "failed_url_file": str(data_dir / "failed_url.txt"),
            "failed_url_file_old": str(data_dir / "failed_url_old.txt"),
            "cookies_path": str(data_dir / "cookies.txt"),
            "download_archive_path": str(data_dir / "download_archive.txt"),
        }

    def _ensure_path_defaults(self):
        """Set default paths only for empty/missing path settings"""
        for key, default_path in self.dynamic_paths.items():
            current_value = self.current_settings.get(key, "")
            if not current_value or current_value == "":
                self.current_settings[key] = default_path

    # def get_app_root(self):
    #     """Get the application root directory"""
    #     if hasattr(sys, "_MEIPASS"):
    #         return Path(sys._MEIPASS)
    #     else:
    #         return Path(__file__).parent.parent


    def get_app_root(self):
        """Get the application root directory"""
        # Make sure frozen check comes first
        if getattr(sys, 'frozen', False):
            # PyInstaller build (onefile or onedir)
            exe_dir = Path(sys.executable).parent
            if (exe_dir / '_internal').exists():
                return exe_dir / '_internal'
            else:
                return Path(sys._MEIPASS)
        else:
            # Development
            return Path(__file__).parent.parent


    def get_persistent_data_dir(self):
        """Get a persistent directory for app data"""
        app_name = "Video Downloader"

        if sys.platform == "win32":
            data_dir = Path(os.environ.get("LOCALAPPDATA", "")) / app_name
        elif sys.platform == "darwin":
            data_dir = Path.home() / "Library" / "Application Support" / app_name
        else:  # Linux
            data_dir = Path.home() / ".local" / "share" / app_name

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

    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        paths_to_create = ["downloads_dir", "data_dir", "bin_dir", "utils_dir", "assets_dir", "docs_dir"]
        for path_key in paths_to_create:
            path = self.get(path_key)
            if path:
                os.makedirs(path, exist_ok=True)

    def _get_settings_path(self):
        """Get path to settings file"""
        if self.is_onefile_build():
            base_dir = self.get_persistent_data_dir()
        else:
            base_dir = self.get_app_root()
        return base_dir / "data" / "settings.json"

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file or return defaults"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    user_settings = json.load(f)
                    
                # Start with defaults, then apply user settings
                merged_settings = self._default_settings.copy()
                merged_settings.update(user_settings)
                return merged_settings

        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            logging.warning(f"Settings loading warning: {e}")

        return self._default_settings.copy()

    def save_settings(self, settings: Dict[str, Any] = None) -> bool:
        """Save settings to file"""
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)

            if settings:
                self.current_settings.update(settings)

            # Save all settings as-is (don't reset paths to empty)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.current_settings, f, indent=4, ensure_ascii=False)

            self._notify_callbacks()
            self._ensure_directories()

            if self.format_change_callback:
                self.format_change_callback()

            return True

        except Exception as e:
            logging.error(f"Settings save error: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self.current_settings.get(key, default)

    def set(self, key: str, value: Any, save: bool = True) -> bool:
        """Set a setting value"""
        old_value = self.current_settings.get(key)
        self.current_settings[key] = value
        
        # Log path changes for debugging
        if key.endswith("_dir") or "path" in key:
            print(f"Settings: Changed {key} from '{old_value}' to '{value}'")
        
        if save:
            return self.save_settings()
        return True

    def get_cookies_cmd(self) -> List[str]:
        """Dynamically generate cookies command based on settings"""
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

    def register_callback(self, callback: callable):
        """Register a callback for settings changes"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def unregister_callback(self, callback: callable):
        """Unregister a callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def _notify_callbacks(self):
        """Notify all registered callbacks about settings changes"""
        for callback in self.callbacks:
            try:
                callback(self.current_settings)
            except Exception as e:
                logging.error(f"Callback error: {e}")

    # def reset_to_defaults(self) -> bool:
    #     """Reset all settings to defaults"""
    #     # Keep dynamic paths, reset other settings
    #     path_backups = {k: v for k, v in self.current_settings.items() 
    #                    if k in self.dynamic_paths.keys()}
        
    #     self.current_settings = self._default_settings.copy()
    #     self.current_settings.update(self.dynamic_paths)  # Restore current dynamic paths
    #     self.current_settings.update(path_backups)  # Restore any user-customized paths
        
    #     return self.save_settings()
        
    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults while preserving dynamic paths"""
        # Get current dynamic paths to preserve them
        current_dynamic_paths = self._calculate_dynamic_paths()
        
        # Reset to base defaults
        self.current_settings = self._default_settings.copy()
        
        # Apply current dynamic paths as defaults
        self.current_settings.update(current_dynamic_paths)
        
        return self.save_settings()    

    def get_all(self):
        """Get all current settings"""
        return self.current_settings.copy()

    def is_healthy(self):
        """Check if settings are in good state"""
        return (
            hasattr(self, "current_settings")
            and self.current_settings is not None
            and len(self.current_settings) > 0
        )
    
# # settings_manager.py
# import json
# import os
# import sys
# from pathlib import Path
# from typing import Dict, Any, List
# import logging


# class SettingsManager:
#     _instance = None

#     # Default settings
#     _default_settings = {
#         # Download settings
#         "download_speed": "10M",
#         "enable_download_archive": False,
#         "stream_and_merge_format": "bestvideo+bestaudio/best-mkv",
#         "auto_update": True,
#         "gui_theme": "Default",
#         "platform_specific_download_folders": False,
#         "multisession_queue_download_support": True,
#         "track_failed_url": True,
#         # Path settings
#         "base_dir": "",
#         "downloads_dir": "",
#         "data_dir": "",
#         "bin_dir": "",
#         "assets_dir": "",
#         "queue_file": "",
#         "queue_file_old": "",
#         "failed_url_file": "",
#         "failed_url_file_old": "",
#         "download_archive_path": "",
#         # Cookies settings
#         "cookies_path": "",
#         "enable_cookies_from_browser": False,
#         "cookies_cmd": [],
#         "cookies_from_browser_cmd": [],
#         "supported_browsers": [
#             "brave",
#             "chrome",
#             "chromium",
#             "edge",
#             "firefox",
#             "opera",
#             "safari",
#             "vivaldi",
#             "whale",
#         ],
#     }

#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super(SettingsManager, cls).__new__(cls)
#             cls._instance._initialize()
#         return cls._instance

#     def _initialize(self):
#         """Initialize settings with portable path calculations"""
#         # Initialize callback FIRST
#         self.format_change_callback = None

#         # Get the base directory (where executable or script is located)
#         if self.is_onefile_build():
#             # PyInstaller onefile - use persistent directory
#             base_dir = self.get_persistent_data_dir()
#             print(f"Using persistent storage: {base_dir}")
#         else:
#             # Development or onedir - use executable directory
#             base_dir = self.get_app_root()

#         # All paths are relative to the executable directory
#         downloads_dir = base_dir / "videos"
#         data_dir = base_dir / "data"
#         bin_dir = base_dir / "bin"
#         assets_dir = base_dir / "assets"

#         # Create directories if they don't exist
#         downloads_dir.mkdir(parents=True, exist_ok=True)
#         data_dir.mkdir(parents=True, exist_ok=True)
#         bin_dir.mkdir(parents=True, exist_ok=True)
#         assets_dir.mkdir(parents=True, exist_ok=True)

#         self._default_settings.update(
#             {
#                 "base_dir": str(base_dir),
#                 "downloads_dir": str(downloads_dir),
#                 "data_dir": str(data_dir),
#                 "bin_dir": str(bin_dir),
#                 "assets_dir": str(assets_dir),
#                 "queue_file": str(data_dir / "queue.txt"),
#                 "queue_file_old": str(data_dir / "queue_old.txt"),
#                 "failed_url_file": str(data_dir / "failed_url.txt"),
#                 "failed_url_file_old": str(data_dir / "failed_url_old.txt"),
#                 "cookies_path": str(data_dir / "cookies.txt"),
#                 "download_archive_path": str(data_dir / "download_archive.txt"),
#             }
#         )

#         # Now load settings
#         self.settings_file = self._get_settings_path()
#         self.current_settings = self._load_settings()
#         self.callbacks = []

#         # FORCE update current settings with new paths
#         self.current_settings.update(
#             {
#                 "base_dir": str(base_dir),
#                 "downloads_dir": str(downloads_dir),
#                 "data_dir": str(data_dir),
#                 "bin_dir": str(bin_dir),
#                 "assets_dir": str(assets_dir),
#             }
#         )

#         # Save the updated settings
#         self.save_settings()

#         # Ensure directories exist
#         self._ensure_directories()
#         self.format_change_callback = None

#     def get_app_root(self):
#         """Get the application root directory"""
#         if hasattr(sys, "_MEIPASS"):
#             # PyInstaller: use the temp extraction directory
#             return Path(sys._MEIPASS)
#         else:
#             # Development: go up from current file location
#             return Path(__file__).parent.parent

#     def get_persistent_data_dir(self):
#         """Get a persistent directory for app data that survives temp cleanup"""
#         app_name = "Video Downloader"

#         if sys.platform == "win32":
#             data_dir = Path(os.environ.get("LOCALAPPDATA", "")) / app_name
#         elif sys.platform == "darwin":
#             data_dir = Path.home() / "Library" / "Application Support" / app_name
#         else:  # Linux
#             data_dir = Path.home() / ".local" / "share" / app_name

#         data_dir.mkdir(parents=True, exist_ok=True)
#         return data_dir

#     def is_onefile_build(self):
#         """Check if running as PyInstaller onefile build"""
#         return (
#             getattr(sys, "frozen", False)
#             and hasattr(sys, "_MEIPASS")
#             and not os.path.exists(
#                 os.path.join(os.path.dirname(sys.executable), "_internal")
#             )
#         )

#     def _ensure_directories(self):
#         """Ensure all necessary directories exist"""
#         os.makedirs(self.get("downloads_dir"), exist_ok=True)
#         os.makedirs(self.get("data_dir"), exist_ok=True)
#         os.makedirs(self.get("bin_dir"), exist_ok=True)

#     def _get_settings_path(self):
#         """Get path to settings file - using persistent storage"""
#         if self.is_onefile_build():
#             base_dir = self.get_persistent_data_dir()
#         else:
#             base_dir = self.get_app_root()
#         return base_dir / "data" / "settings.json"

#     def _load_settings(self) -> Dict[str, Any]:
#         """Load settings from file or return defaults with dynamic paths"""
#         try:
#             if self.settings_file.exists():
#                 with open(self.settings_file, "r", encoding="utf-8") as f:
#                     user_settings = json.load(f)

#                     # For path settings, if user hasn't customized them, use dynamic defaults
#                     path_keys = [
#                         "base_dir",
#                         "downloads_dir",
#                         "data_dir",
#                         "bin_dir",
#                         "assets_dir",
#                         "queue_file",
#                         "queue_file_old",
#                         "failed_url_file",
#                         "failed_url_file_old",
#                         "cookies_path",
#                         "download_archive_path",
#                     ]

#                     for key in path_keys:
#                         if key not in user_settings or user_settings[key] == "":
#                             user_settings[key] = self._default_settings[key]

#                     return {**self._default_settings, **user_settings}

#         except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
#             logging.warning(f"Settings loading warning: {e}")

#         return self._default_settings.copy()

#     def save_settings(self, settings: Dict[str, Any] = None) -> bool:
#         """Save settings to file"""
#         try:
#             self.settings_file.parent.mkdir(parents=True, exist_ok=True)

#             if settings:
#                 self.current_settings = {**self.current_settings, **settings}

#             # Don't save dynamic paths if they match defaults (to avoid clutter)
#             settings_to_save = self.current_settings.copy()
#             path_keys = [
#                 "base_dir",
#                 "downloads_dir",
#                 "data_dir",
#                 "bin_dir",
#                 "assets_dir",
#                 "queue_file",
#                 "queue_file_old",
#                 "failed_url_file",
#                 "failed_url_file_old",
#                 "cookies_path",
#                 "download_archive_path",
#             ]

#             for key in path_keys:
#                 if settings_to_save[key] == self._default_settings[key]:
#                     settings_to_save[key] = (
#                         ""  # Save as empty to indicate "use default"
#                     )

#             with open(self.settings_file, "w", encoding="utf-8") as f:
#                 json.dump(settings_to_save, f, indent=4, ensure_ascii=False)

#             self._notify_callbacks()
#             self._ensure_directories()

#             if self.format_change_callback:
#                 self.format_change_callback()

#             return True

#         except Exception as e:
#             logging.error(f"Settings save error: {e}")
#             return False

#     def get(self, key: str, default: Any = None) -> Any:
#         """Get a setting value"""
#         return self.current_settings.get(key, default)

#     def set(self, key: str, value: Any, save: bool = True) -> bool:
#         """Set a setting value"""
#         self.current_settings[key] = value
#         if save:
#             return self.save_settings()
#         return True

#     def get_cookies_cmd(self) -> List[str]:
#         """Dynamically generate cookies command based on settings"""
#         cookies_cmd = []

#         # Cookies from file
#         cookies_path = self.get("cookies_path")
#         if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
#             cookies_cmd.extend(["--cookies", cookies_path])

#         # Cookies from browser
#         if self.get("enable_cookies_from_browser"):
#             cookies_cmd.extend(["--cookies-from-browser", "chrome"])  # Default browser

#         return cookies_cmd

#     def register_callback(self, callback: callable):
#         """Register a callback for settings changes"""
#         if callback not in self.callbacks:
#             self.callbacks.append(callback)

#     def unregister_callback(self, callback: callable):
#         """Unregister a callback"""
#         if callback in self.callbacks:
#             self.callbacks.remove(callback)

#     def _notify_callbacks(self):
#         """Notify all registered callbacks about settings changes"""
#         for callback in self.callbacks:
#             try:
#                 callback(self.current_settings)
#             except Exception as e:
#                 logging.error(f"Callback error: {e}")

#     def reset_to_defaults(self) -> bool:
#         """Reset all settings to defaults"""
#         self.current_settings = self._default_settings.copy()
#         return self.save_settings()

#     def is_using_defaults(self) -> bool:
#         """Check if using default settings"""
#         return self.get("use_default_settings", True)

#     def get_all(self):
#         """Get all current settings"""
#         return self.current_settings.copy()

#     def is_healthy(self):
#         """Check if settings are in good state"""
#         return (
#             hasattr(self, "current_settings")
#             and self.current_settings is not None
#             and len(self.current_settings) > 0
#         )
