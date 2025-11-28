"""Video processing tools"""

# Import downloader module
try:
    from . import downloader
    from .downloader import VideoDownloader, download_video_cli

    __all__ = ["downloader", "VideoDownloader", "download_video_cli"]
except ImportError:
    __all__ = []
