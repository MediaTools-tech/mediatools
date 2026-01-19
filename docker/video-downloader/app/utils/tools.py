"""
Tool utilities for managing external tools (FFmpeg, yt-dlp, spotdl, deno).
Adapted for Docker deployment with Linux-only support.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import requests
from datetime import datetime, timedelta

from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


class FFmpegTool:
    """FFmpeg tool manager."""
    
    def __init__(self):
        self.settings = settings_manager
    
    def get_ffmpeg_path(self) -> str:
        """Get path to ffmpeg. Uses system-installed version in Docker."""
        # Check for system-installed ffmpeg first
        if shutil.which("ffmpeg"):
            return "ffmpeg"
        
        # Check bin folder
        bin_path = self.settings.get_bin_folder() / "ffmpeg"
        if bin_path.exists():
            return str(bin_path)
        
        return "ffmpeg"
    
    def get_ffprobe_path(self) -> str:
        """Get path to ffprobe."""
        if shutil.which("ffprobe"):
            return "ffprobe"
        
        bin_path = self.settings.get_bin_folder() / "ffprobe"
        if bin_path.exists():
            return str(bin_path)
        
        return "ffprobe"
    
    def is_available(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                [self.get_ffmpeg_path(), "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_version(self) -> Optional[str]:
        """Get FFmpeg version string."""
        try:
            result = subprocess.run(
                [self.get_ffmpeg_path(), "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # First line contains version
                first_line = result.stdout.split('\n')[0]
                return first_line
        except Exception:
            pass
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive FFmpeg status."""
        available = self.is_available()
        version = self.get_version() if available else None
        
        # Check for codec support
        has_libopus = False
        has_libvorbis = False
        
        if available:
            try:
                result = subprocess.run(
                    [self.get_ffmpeg_path(), "-codecs"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout
                has_libopus = "libopus" in output
                has_libvorbis = "libvorbis" in output
            except Exception:
                pass
        
        return {
            "available": available,
            "path": self.get_ffmpeg_path(),
            "version": version,
            "has_libopus": has_libopus,
            "has_libvorbis": has_libvorbis
        }


class YtdlpTool:
    """yt-dlp tool manager (uses Python package)."""
    
    def __init__(self):
        self.settings = settings_manager
    
    def is_available(self) -> bool:
        """Check if yt-dlp is available."""
        try:
            import yt_dlp
            return True
        except ImportError:
            return False
    
    def get_version(self) -> Optional[str]:
        """Get yt-dlp version."""
        try:
            import yt_dlp
            return yt_dlp.version.__version__
        except Exception:
            return None
    
    def get_latest_version(self) -> Optional[str]:
        """Get latest yt-dlp version from GitHub."""
        try:
            response = requests.get(
                "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("tag_name", "").lstrip("v")
        except Exception:
            pass
        return None
    
    def check_update_needed(self) -> bool:
        """Check if yt-dlp update is needed (weekly check)."""
        last_check = self.settings.get("last_ytdlp_update_check", "")
        
        if last_check:
            try:
                last_date = datetime.fromisoformat(last_check)
                if datetime.now() - last_date < timedelta(days=7):
                    return False
            except ValueError:
                pass
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get yt-dlp status."""
        return {
            "available": self.is_available(),
            "version": self.get_version(),
            "type": "python_package"
        }


class SpotdlTool:
    """spotdl tool manager (uses Python package)."""
    
    def __init__(self):
        self.settings = settings_manager
    
    def is_available(self) -> bool:
        """Check if spotdl is available."""
        try:
            import spotdl
            return True
        except ImportError:
            # Try CLI
            return shutil.which("spotdl") is not None
    
    def get_version(self) -> Optional[str]:
        """Get spotdl version."""
        try:
            import spotdl
            return spotdl.__version__
        except Exception:
            pass
        
        # Try CLI
        try:
            result = subprocess.run(
                ["spotdl", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get spotdl status."""
        return {
            "available": self.is_available(),
            "version": self.get_version(),
            "type": "python_package"
        }


class DenoTool:
    """Deno tool manager (download on demand)."""
    
    DENO_INSTALL_URL = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip"
    
    def __init__(self):
        self.settings = settings_manager
        self._deno_path = None
    
    def get_deno_path(self) -> Path:
        """Get path to deno binary."""
        return self.settings.get_bin_folder() / "deno"
    
    def is_available(self) -> bool:
        """Check if deno is available."""
        deno_path = self.get_deno_path()
        return deno_path.exists() and os.access(deno_path, os.X_OK)
    
    def get_version(self) -> Optional[str]:
        """Get deno version."""
        if not self.is_available():
            return None
        
        try:
            result = subprocess.run(
                [str(self.get_deno_path()), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # First line is deno version
                return result.stdout.split('\n')[0]
        except Exception:
            pass
        
        return None
    
    def needs_update(self) -> bool:
        """Check if deno needs monthly update."""
        last_check = self.settings.get("last_deno_update_check", "")
        
        if not last_check:
            return True
        
        try:
            last_date = datetime.fromisoformat(last_check)
            return datetime.now() - last_date > timedelta(days=30)
        except ValueError:
            return True
    
    def download(self, progress_callback=None) -> bool:
        """Download deno binary."""
        import zipfile
        import io
        
        try:
            if progress_callback:
                progress_callback("Downloading deno...")
            
            response = requests.get(self.DENO_INSTALL_URL, stream=True, timeout=300)
            response.raise_for_status()
            
            # Extract from zip
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                deno_path = self.get_deno_path()
                deno_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Extract deno binary
                with zf.open("deno") as source, open(deno_path, "wb") as target:
                    target.write(source.read())
                
                # Make executable
                os.chmod(deno_path, 0o755)
            
            # Update last check time
            self.settings.set("last_deno_update_check", datetime.now().isoformat())
            
            if progress_callback:
                progress_callback("Deno downloaded successfully")
            
            logger.info(f"Deno downloaded to {deno_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download deno: {e}")
            if progress_callback:
                progress_callback(f"Failed to download deno: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get deno status."""
        return {
            "available": self.is_available(),
            "version": self.get_version(),
            "path": str(self.get_deno_path()),
            "needs_update": self.needs_update()
        }


class ToolManager:
    """Unified tool manager."""
    
    def __init__(self):
        self.ffmpeg = FFmpegTool()
        self.ytdlp = YtdlpTool()
        self.spotdl = SpotdlTool()
        self.deno = DenoTool()
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all tools."""
        return {
            "ffmpeg": self.ffmpeg.get_status(),
            "ytdlp": self.ytdlp.get_status(),
            "spotdl": self.spotdl.get_status(),
            "deno": self.deno.get_status()
        }
    
    def check_required_tools(self) -> Dict[str, bool]:
        """Check if required tools are available."""
        return {
            "ffmpeg": self.ffmpeg.is_available(),
            "ytdlp": self.ytdlp.is_available(),
            "spotdl": self.spotdl.is_available()
        }
    
    def ensure_deno(self, progress_callback=None) -> bool:
        """Ensure deno is available, download if needed."""
        if self.deno.is_available() and not self.deno.needs_update():
            return True
        
        return self.deno.download(progress_callback)


# Singleton instance
tool_manager = ToolManager()
