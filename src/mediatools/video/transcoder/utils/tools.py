import os
import platform
import subprocess
import requests
import zipfile
import tarfile
import shutil
import time
import re
from pathlib import Path

class FFmpegTool:
    # Platform-specific filenames
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
        system = platform.system().lower()
        if "windows" in system or "win32" in system:
            self.current_platform = "Windows"
        elif "darwin" in system:
            self.current_platform = "Darwin"
        else:
            self.current_platform = "Linux"

    def get_ffmpeg_path(self):
        """Always returns the LOCAL path where FFmpeg SHOULD be"""
        bin_dir = self.settings.get("bin_dir", "bin")
        return str(Path(bin_dir) / self.LOCAL_FILENAMES_FFMPEG[self.current_platform])

    def get_ffprobe_path(self):
        """Always returns the LOCAL path where FFprobe SHOULD be"""
        bin_dir = self.settings.get("bin_dir", "bin")
        return str(Path(bin_dir) / self.LOCAL_FILENAMES_FFPROBE[self.current_platform])

    def get_ffmpeg_command(self):
        """Returns local path if it exists, otherwise 'ffmpeg'"""
        path = self.get_ffmpeg_path()
        return path if os.path.exists(path) else "ffmpeg"

    def get_ffprobe_command(self):
        """Returns local path if it exists, otherwise 'ffprobe'"""
        path = self.get_ffprobe_path()
        return path if os.path.exists(path) else "ffprobe"

    def is_ffmpeg_downloaded(self):
        """Check if both binaries exist in the local bin directory"""
        return os.path.exists(self.get_ffmpeg_path()) and os.path.exists(self.get_ffprobe_path())

    def is_ffmpeg_available(self):
        """Check if FFmpeg is either downloaded locally or available system-wide"""
        if self.is_ffmpeg_downloaded():
            return True
        try:
            IS_WINDOWS = self.current_platform == "Windows"
            process_kwargs = {"capture_output": True, "check": True}
            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                
            subprocess.run(["ffmpeg", "-version"], **process_kwargs)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_ffmpeg_latest_url(self):
        """Return the download URL for the current platform"""
        return self.FFMPEG_DOWNLOAD_URLS.get(self.current_platform)

    def get_ffmpeg_status(self):
        """Return a dictionary of FFmpeg status info"""
        return {
            "is_ffmpeg_downloaded": self.is_ffmpeg_downloaded(),
            "is_ffmpeg_available": self.is_ffmpeg_available(),
            "ffmpeg_path": self.get_ffmpeg_path(),
            "ffprobe_path": self.get_ffprobe_path(),
            "ffmpeg_latest_url": self.get_ffmpeg_latest_url(),
        }

    def _normalize_version(self, ver_str):
        """Helper to extract a comparable version number (e.g., '8.0') from various strings"""
        if not ver_str:
            return ""
        # Handle cases like "ffmpeg version 8.0-essentials_build..."
        # We want the '8.0' part.
        import re
        match = re.search(r'(\d+\.\d+)', ver_str)
        if match:
            return match.group(1)
        return ver_str.split('-')[0].strip().lower()

    def get_local_version(self):
        """Get the version of the local FFmpeg binary"""
        path = self.get_ffmpeg_path()
        if not os.path.exists(path):
            return None
            
        try:
            IS_WINDOWS = self.current_platform == "Windows"
            process_kwargs = {"capture_output": True, "text": True}
            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                
            result = subprocess.run([path, "-version"], **process_kwargs)
            # Example: "ffmpeg version 8.0-essentials_build..."
            first_line = result.stdout.split('\n')[0]
            import re
            match = re.search(r'version\s+([^\s,]+)', first_line)
            return match.group(1) if match else "unknown"
        except Exception:
            return "unknown"

    def get_remote_version(self):
        """Estimate the remote version from the download URL"""
        url = self.get_ffmpeg_latest_url()
        if not url:
            return None
        
        # Example URLs:
        # .../releases/download/8.0/ffmpeg-8.0-full_build.zip
        import re
        match = re.search(r'(\d+\.\d+)', url)
        return match.group(1) if match else "latest"

    def is_up_to_date(self):
        """Check if local FFmpeg version matches remote version"""
        local = self._normalize_version(self.get_local_version())
        remote = self._normalize_version(self.get_remote_version())
        if not local or local == "unknown":
            return False
        return remote in local or local == remote

    def _terminate_local_processes(self):
        """Attempt to kill any running ffmpeg/ffprobe processes in the bin directory (Windows only)"""
        if self.current_platform != "Windows":
            return
            
        try:
            # Creation flags to hide the window
            process_kwargs = {"capture_output": True}
            if self.current_platform == "Windows":
                 process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                 
            # We use taskkill to be thorough. We target by image name.
            # Using /F for force and /T for tree.
            subprocess.run(["taskkill", "/F", "/T", "/IM", "ffmpeg.exe"], **process_kwargs)
            subprocess.run(["taskkill", "/F", "/T", "/IM", "ffprobe.exe"], **process_kwargs)
            time.sleep(2) # Give OS more time to release handles
        except Exception:
            pass

    def _safe_replace(self, src_path, dst_path):
        """Safely replace a file, handling 'file in use' errors on Windows with multiple retries"""
        src = Path(src_path)
        dst = Path(dst_path)
        
        if not src.exists():
            return False
            
        if src.resolve() == dst.resolve():
            return True

        # Try up to 5 times to replace the file with increasing delay
        for attempt in range(5):
            try:
                if dst.exists():
                    # Check if it's the same file (size and mtime might match if already updated)
                    # But usually we want to force replace to be sure.
                    
                    backup = dst.with_suffix(".old")
                    if backup.exists():
                        try: os.remove(backup)
                        except: pass
                    
                    try:
                        os.rename(str(dst), str(backup))
                    except OSError:
                        # Fallback to direct removal attempt
                        try: os.remove(str(dst))
                        except: pass
                
                if not dst.exists() or attempt > 0:
                    os.rename(str(src), str(dst))
                    return True
            except OSError as e:
                if attempt < 4:
                    # Exponential backoff: 1s, 2s, 4s, 8s
                    time.sleep(pow(2, attempt)) 
                    # Try to kill processes again just in case a new one started
                    self._terminate_local_processes()
                    continue
                raise e
        return False

    def download_and_extract(self, progress_callback=None):
        """Download and extract FFmpeg to the bin directory"""
        url = self.get_ffmpeg_latest_url()
        if not url:
            raise ValueError(f"No download URL for {self.current_platform}")
            
        bin_dir = Path(self.settings.get("bin_dir", "bin"))
        bin_dir.mkdir(parents=True, exist_ok=True)
        archive_path = bin_dir / "ffmpeg_download.tmp"
        
        # 0. Cleanup running processes to release handles
        self._terminate_local_processes()

        # 1. Download
        if progress_callback:
            progress_callback(0, "Downloading FFmpeg...")
            
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        downloaded = 0
        with open(archive_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        percent = (downloaded / total_size) * 100
                        progress_callback(percent, f"Downloading FFmpeg: {percent:.1f}%")

        # 2. Extract
        if progress_callback:
            progress_callback(100, "Extracting FFmpeg...")
            
        ffmpeg_final = self.get_ffmpeg_path()
        ffprobe_final = self.get_ffprobe_path()
        
        # We use a temp subfolder to avoid extracting directly over active files
        temp_extract = bin_dir / "temp_extract"
        if temp_extract.exists():
            shutil.rmtree(temp_extract)
        temp_extract.mkdir(parents=True, exist_ok=True)

        extracted_ffmpeg = None
        extracted_ffprobe = None

        try:
            if self.current_platform in ["Windows", "Darwin"]:
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    for member in zip_ref.namelist():
                        if member.endswith(self.LOCAL_FILENAMES_FFMPEG[self.current_platform]):
                            zip_ref.extract(member, path=temp_extract)
                            extracted_ffmpeg = temp_extract / member
                        elif member.endswith(self.LOCAL_FILENAMES_FFPROBE[self.current_platform]):
                            zip_ref.extract(member, path=temp_extract)
                            extracted_ffprobe = temp_extract / member
            else: # Linux
                 with tarfile.open(archive_path, "r:xz") as tar:
                    for member in tar.getmembers():
                        if member.name.endswith("/" + self.LOCAL_FILENAMES_FFMPEG["Linux"]):
                            tar.extract(member, temp_extract)
                            extracted_ffmpeg = temp_extract / member.name
                        elif member.name.endswith("/" + self.LOCAL_FILENAMES_FFPROBE["Linux"]):
                            tar.extract(member, temp_extract)
                            extracted_ffprobe = temp_extract / member.name

            # 3. Move files (after closing the archive)
            if extracted_ffmpeg:
                self._safe_replace(extracted_ffmpeg, ffmpeg_final)
            if extracted_ffprobe:
                self._safe_replace(extracted_ffprobe, ffprobe_final)
                
            # Permissions
            if self.current_platform != "Windows":
                 try:
                     os.chmod(ffmpeg_final, 0o755)
                     os.chmod(ffprobe_final, 0o755)
                 except: pass
                 
        finally:
            # Cleanup
            if archive_path.exists():
                archive_path.unlink()
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
                
            # Cleanup any other subdirs (like the one created by nested zip structure)
            for item in bin_dir.iterdir():
                if item.is_dir() and item.name not in ["data", "transcoded"]:
                     try: shutil.rmtree(item)
                     except: pass

        return True
