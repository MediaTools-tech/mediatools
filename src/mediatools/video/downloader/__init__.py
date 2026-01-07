import os
import sys
from .core.settings_manager import SettingsManager

def get_version():
    """
    Reads the version from the version.txt file using the SettingsManager
    to correctly resolve the data path.
    """
    try:
        # SettingsManager correctly resolves the data path for both dev and prod.
        settings = SettingsManager()
        data_dir = settings.get("data_dir")
        version_path = os.path.join(data_dir, 'version.txt')
        with open(version_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return "unknown"

__version__ = get_version()

from .core.download_service import DownloadService
from .core.queue_manager import QueueManager


class VideoDownloader:
    """Main video downloader class that wraps your existing functionality"""

    def __init__(self):
        self.settings_manager = SettingsManager()
        self.download_service = DownloadService()
        self.queue_manager = QueueManager()

    def download(self, url, output_dir=None, quality=None):
        """Simple download method for library users"""
        return self.download_service.download(url, output_dir, quality)

    def add_to_queue(self, urls):
        """Add URLs to download queue"""
        return self.queue_manager.add_urls(urls)


def download_video_cli(url, output_dir="downloads", quality="best"):
    """Simple function for CLI usage"""
    downloader = VideoDownloader()
    return downloader.download(url, output_dir, quality)


__all__ = [
    "VideoDownloader",
    "download_video_cli",
    "DownloadService",
    "QueueManager",
    "SettingsManager",
]
