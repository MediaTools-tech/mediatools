import os
import platform
from pathlib import Path
import subprocess


class FFmpegTool:
    # Platform-specific filenames (these are constants, not settings)
    LOCAL_FILENAMES_FFMPEG = {
        "Windows": "ffmpeg.exe",
        "Linux": "ffmpeg",
        "Darwin": "ffmpeg",
    }

    LOCAL_FILENAMES_FFPROBE = {
        "Windows": "ffprobe.exe",
        "Linux": "ffprobe",
        "Darwin": "ffprobe",
    }

    FFMPEG_DOWNLOAD_URLS = {
        "Windows": "https://github.com/GyanD/codexffmpeg/releases/download/8.0/ffmpeg-8.0-full_build.zip",
        "Linux": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
        "Darwin": "https://evermeet.cx/ffmpeg/ffmpeg-8.0.zip",
    }

    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.current_platform = platform.system()

    def get_ffmpeg_path(self):
        """Get the full path to ffmpeg executable"""
        bin_dir = self.settings.get("bin_dir", "bin")  # Get from settings or default
        return str(Path(bin_dir) / self.LOCAL_FILENAMES_FFMPEG[self.current_platform])

    def get_ffprobe_path(self):
        """Get the full path to ffprobe executable"""
        bin_dir = self.settings.get("bin_dir", "bin")  # Get from settings or default
        return str(Path(bin_dir) / self.LOCAL_FILENAMES_FFPROBE[self.current_platform])

    def is_ffmpeg_suite_installed(self):
        """Check if FFmpeg is installed systemwide"""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def is_ffmpeg_downloaded(self):
        """Check if FFmpeg is downloaded in our bin directory"""
        ffmpeg_path = self.get_ffmpeg_path()
        ffprobe_path = self.get_ffprobe_path()
        return os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path)

    def is_ffmpeg_available(self):
        """Check if FFmpeg is available (either systemwide or downloaded)"""
        return self.is_ffmpeg_suite_installed() or self.is_ffmpeg_downloaded()

    def get_ffmpeg_latest_url(self):
        """Get the url for latest ffmpeg version"""
        return self.FFMPEG_DOWNLOAD_URLS[self.current_platform]

    def get_ffmpeg_status(self):
        """Get comprehensive FFmpeg status"""
        return {
            "is_ffmpeg_suite_installed": self.is_ffmpeg_suite_installed(),
            "is_ffmpeg_suite_downloaded": self.is_ffmpeg_downloaded(),
            "is_ffmpeg_suite_available": self.is_ffmpeg_available(),
            "ffmpeg_path": self.get_ffmpeg_path(),
            "ffprobe_path": self.get_ffprobe_path(),
            "ffmpeg_latest_url": self.get_ffmpeg_latest_url(),
        }


class YtdlpTool:

    # Platform-specific download URLs
    GITHUB_DOWNLOAD_URLS = {
        "Windows": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
        "Linux": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
        "Darwin": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
    }

    # URL for checking latest version
    GITHUB_API_LATEST = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"

    LOCAL_FILENAMES_YTDLP = {
        "Windows": "yt-dlp.exe",
        "Linux": "yt-dlp",
        "Darwin": "yt-dlp_macos",
    }

    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.current_platform = platform.system()

    def get_ytdlp_path(self):
        """Get the full path to yt-dlp executable"""
        bin_dir = self.settings.get("bin_dir", "bin")  # Get from settings or default
        return str(Path(bin_dir) / self.LOCAL_FILENAMES_YTDLP[self.current_platform])

    def is_ytdlp_available(self):
        """Check if ytdlp is available"""
        ytdlp_path = self.get_ytdlp_path()
        return os.path.exists(ytdlp_path)

    def get_ytdlp_latest_rul(self):
        """Get the url for latest ytdlp version"""
        return self.GITHUB_DOWNLOAD_URLS[self.current_platform]

    def get_ytdlp_github_api_latest(self):
        """Get ytdlp github api latest"""
        return self.GITHUB_API_LATEST

    def get_ytdlp_status(self):
        """Get comprehensive ytdlp status"""
        return {
            "is_ytdlp_suite_installed": self.is_ytdlp_available(),
            "ytdlp_path": self.get_ytdlp_path(),
            "ytdlp_latest_url": self.get_ytdlp_latest_rul(),
            "ytdlp_github_api_latest": self.get_ytdlp_github_api_latest(),
        }
