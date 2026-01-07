import os
import platform
from pathlib import Path
import subprocess
import requests
import time

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
            # Determine platform
            IS_WINDOWS = platform.system() == "Windows"
            process_kwargs = {"capture_output": True, "check": True}
            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            subprocess.run(["ffmpeg", "-version"], **process_kwargs)
            subprocess.run(["ffprobe", "-version"], **process_kwargs)
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

# can you modify this for crosssplatform supported get_ytdlp_latest_version() and get_ytdlp_current_version()
# class YtdlpTool:

#     # Platform-specific download URLs
#     GITHUB_DOWNLOAD_URLS = {
#         "Windows": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
#         "Linux": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
#         "Darwin": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
#     }

#     # URL for checking latest version
#     GITHUB_API_LATEST = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"

#     LOCAL_FILENAMES_YTDLP = {
#         "Windows": "yt-dlp.exe",
#         "Linux": "yt-dlp",
#         "Darwin": "yt-dlp",
#     }

#     def __init__(self, settings_manager):
#         self.settings = settings_manager
#         self.current_platform = platform.system()

#     def get_ytdlp_path(self):
#         """Get the full path to yt-dlp executable"""
#         bin_dir = self.settings.get("bin_dir", "bin")  # Get from settings or default
#         return str(Path(bin_dir) / self.LOCAL_FILENAMES_YTDLP[self.current_platform])

#     def is_ytdlp_available(self):
#         """Check if ytdlp is available"""
#         ytdlp_path = self.get_ytdlp_path()
#         return os.path.exists(ytdlp_path)

#     def get_ytdlp_latest_rul(self):
#         """Get the url for latest ytdlp version"""
#         return self.GITHUB_DOWNLOAD_URLS[self.current_platform]

#     def get_ytdlp_github_api_latest(self):
#         """Get ytdlp github api latest"""
#         return self.GITHUB_API_LATEST

#     def get_ytdlp_status(self):
#         """Get comprehensive ytdlp status"""
#         return {
#             "is_ytdlp_downloaded": self.is_ytdlp_available(),
#             "ytdlp_path": self.get_ytdlp_path(),
#             "ytdlp_latest_url": self.get_ytdlp_latest_rul(),
#             "ytdlp_github_api_latest": self.get_ytdlp_github_api_latest(),
#         }



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
        "Darwin": "yt-dlp",
    }

    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.current_platform = platform.system()
        self.bin_dir = Path(settings_manager.get("bin_dir", "bin"))

    def get_ytdlp_path(self):
        """Get the full path to yt-dlp executable"""
        return str(self.bin_dir / self.LOCAL_FILENAMES_YTDLP[self.current_platform])

    def is_ytdlp_downloaded(self):
        """Check if yt-dlp is downloaded to bin folder"""
        ytdlp_path = self.get_ytdlp_path()
        
        if not os.path.exists(ytdlp_path):
            return False
        
        # Check file size
        file_size = os.path.getsize(ytdlp_path)
        if file_size == 0:
            print(f"Warning: yt-dlp file exists but is empty (0 bytes)")
            return False
        
        # Platform-specific validation
        if self.current_platform == "Windows":
            # Check if it's a valid Windows executable
            try:
                with open(ytdlp_path, 'rb') as f:
                    magic = f.read(2)
                    if magic != b'MZ':
                        print(f"Warning: yt-dlp file doesn't appear to be a valid Windows executable")
                        return False
            except Exception:
                pass  # Don't fail if we can't read
        
        elif self.current_platform in ["Darwin", "Linux"]:
            # Check if executable or can be made executable
            if not os.access(ytdlp_path, os.X_OK):
                try:
                    os.chmod(ytdlp_path, 0o755)
                except Exception as e:
                    print(f"Warning: yt-dlp exists but is not executable and cannot be made executable: {e}")
                    return False
        
        return True

    def get_ytdlp_current_version(self):
        """Get the currently installed yt-dlp version from bin folder.
        
        Returns:
            str: yt-dlp version string if available, None otherwise
        """
        if not self.is_ytdlp_downloaded():
            return None
        
        try:
            ytdlp_path = self.get_ytdlp_path()
            
            # Prepare subprocess arguments
            kwargs = {
                "capture_output": True,
                "text": True,
                "timeout": 10,
            }
            
            # Platform-specific process creation flags
            if self.current_platform == "Windows":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            elif self.current_platform in ["Darwin", "Linux"]:
                # Ensure the file is executable
                if not os.access(ytdlp_path, os.X_OK):
                    os.chmod(ytdlp_path, 0o755)
            
            # Try running yt-dlp with --version flag
            result = subprocess.run(
                [ytdlp_path, "--version"],
                **kwargs
            )
            
            if result.returncode == 0:
                version_output = result.stdout.strip()
                # yt-dlp outputs version like: "2024.04.09" or "2024.04.09.232843"
                # Clean up any extra text
                import re
                match = re.search(r'(\d{4}\.\d{2}\.\d{2}(?:\.\d+)?)', version_output)
                if match:
                    return match.group(1)
            
            # Try alternative method: run without arguments and parse output
            result = subprocess.run(
                [ytdlp_path],
                **kwargs
            )
            
            if result.returncode != 0:  # Most CLIs return non-zero when run without args
                output = result.stdout.strip() + result.stderr.strip()
                import re
                match = re.search(r'version\s+(\d{4}\.\d{2}\.\d{2}(?:\.\d+)?)', output, re.IGNORECASE)
                if match:
                    return match.group(1)
                
        except (subprocess.SubprocessError, OSError, TimeoutError) as e:
            print(f"Error getting yt-dlp current version: {e}")
        except Exception as e:
            print(f"Unexpected error getting yt-dlp current version: {e}")
        
        return None

    def get_ytdlp_latest_version(self):
        """Get the latest available yt-dlp version from GitHub.
        
        Returns:
            str: Latest version string if available, None otherwise
        """
        try:
            import requests
            
            # Set headers to avoid rate limiting
            headers = {
                "User-Agent": "VideoDownloader/1.0",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(
                self.GITHUB_API_LATEST,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract version from tag_name (e.g., "2024.04.09")
                tag_name = data.get("tag_name", "")
                if tag_name:
                    # Remove leading 'v' if present
                    version = tag_name.lstrip('v')
                    return version
                
                # Alternative: check assets for version in filename
                assets = data.get("assets", [])
                for asset in assets:
                    name = asset.get("name", "")
                    if "yt-dlp" in name:
                        # Extract version from filename
                        import re
                        match = re.search(r'(\d{4}\.\d{2}\.\d{2}(?:\.\d+)?)', name)
                        if match:
                            return match.group(1)
        
        except requests.RequestException as e:
            print(f"Error fetching latest yt-dlp version from GitHub: {e}")
        except (KeyError, ValueError, AttributeError) as e:
            print(f"Error parsing GitHub API response for yt-dlp: {e}")
        except Exception as e:
            print(f"Unexpected error getting yt-dlp latest version: {e}")
        
        return None

    def get_ytdlp_latest_url(self):
        """Get the url for latest yt-dlp version"""
        return self.GITHUB_DOWNLOAD_URLS[self.current_platform]

    def get_ytdlp_github_api_latest(self):
        """Get yt-dlp github api latest"""
        return self.GITHUB_API_LATEST

    def get_ytdlp_status(self):
        """Get comprehensive yt-dlp status"""
        current_version = self.get_ytdlp_current_version()
        latest_version = self.get_ytdlp_latest_version()
        
        # Debug logging
        print(f"Current yt-dlp Version: {current_version}")
        print(f"Latest yt-dlp Version: {latest_version}")
        
        # Check if update is available
        update_available = self._is_update_available(current_version, latest_version)
        
        return {
            "is_ytdlp_downloaded": self.is_ytdlp_downloaded(),
            "ytdlp_current_version": current_version,
            "ytdlp_latest_version": latest_version,
            "ytdlp_path": self.get_ytdlp_path(),
            "ytdlp_latest_url": self.get_ytdlp_latest_url(),
            "ytdlp_github_api_latest": self.get_ytdlp_github_api_latest(),
            "update_available": update_available,
            "platform": self.current_platform,
            "is_executable": os.access(self.get_ytdlp_path(), os.X_OK) if os.path.exists(self.get_ytdlp_path()) else False,
        }

    def _is_update_available(self, current_version, latest_version):
        """Check if a yt-dlp update is available"""
        if not current_version or not latest_version:
            return False
        
        try:
            # Parse version strings (format: YYYY.MM.DD or YYYY.MM.DD.revision)
            current_parts = current_version.split(".")
            latest_parts = latest_version.split(".")
            
            # Convert to integers for comparison
            for i in range(min(len(current_parts), len(latest_parts))):
                try:
                    cur_num = int(current_parts[i])
                    lat_num = int(latest_parts[i])
                    
                    if lat_num > cur_num:
                        return True
                    elif lat_num < cur_num:
                        return False
                except ValueError:
                    # If we can't convert to int, compare as strings
                    if latest_parts[i] > current_parts[i]:
                        return True
                    elif latest_parts[i] < current_parts[i]:
                        return False
            
            # All compared parts equal, check if latest has more parts (e.g., 2024.04.09.1 vs 2024.04.09)
            return len(latest_parts) > len(current_parts)
            
        except (ValueError, AttributeError, IndexError) as e:
            print(f"Error comparing versions '{current_version}' vs '{latest_version}': {e}")
            return False

class SpotdlTool:

    # Platform-specific filenames (consistent with FFmpegTool)

    LOCAL_FILENAME_SPOTDL = {

        "Windows": "spotdl.exe",

        "Linux": "spotdl",

        "Darwin": "spotdl",

    }



    # GitHub release information

    GITHUB_REPO = "spotDL/spotify-downloader"

    GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    GITHUB_RELEASES = f"https://github.com/{GITHUB_REPO}/releases"



    def __init__(self, settings_manager):

        self.settings = settings_manager

        self.current_platform = platform.system()

        self.platform_patterns = {

            "Windows": [r"spotdl-.*\.exe", r"spotdl.*win.*\.exe", r".*windows.*\.exe"],

            "Linux": [r"spotdl-.*linux.*", r"spotdl.*linux", r".*linux.*"],

            "Darwin": [r"spotdl-.*darwin.*", r"spotdl-.*macos.*", r"spotdl.*mac.*", r".*darwin.*", r".*macos.*"]

        }



    # def get_spotdl_path(self):

    #     """Get the full path to spotdl executable"""

    #     bin_dir = self.settings.get("bin_dir", "bin")

    #     return str(Path(bin_dir) / self.LOCAL_FILENAME_SPOTDL[self.current_platform])

    # def is_spotdl_downloaded(self):

    #     """Check if SpotDL is installed systemwide (via pip)"""

    #     try:

    #         result = subprocess.run(

    #             ["spotdl", "--version"],

    #             capture_output=True,

    #             text=True,

    #             timeout=5

    #         )

    #         return result.returncode == 0

    #     except (subprocess.CalledProcessError, FileNotFoundError):

    #         return False

    # def is_spotdl_downloaded(self):

    #     """Check if SpotDL is downloaded in our bin directory"""

    #     spotdl_path = self.get_spotdl_path()

    #     return os.path.exists(spotdl_path) and os.path.getsize(spotdl_path) > 1024

    def get_spotdl_current_version(self):
        """Get SpotDL version if available"""
        
        kwargs = {
            "capture_output": True,
            "text": True,
        }
        if self.current_platform == "Windows":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        # Try downloaded version first
        if self.is_spotdl_downloaded():
            try:
                spotdl_path = self.get_spotdl_path()
                result = subprocess.run(
                    [spotdl_path, "--version"],
                    timeout=15,
                    **kwargs
                )
                if result.returncode == 0:
                    return self._extract_version(result.stdout.strip())
            except:
                pass
        
        # Try systemwide version
        if self.is_spotdl_downloaded():
            try:
                result = subprocess.run(
                    ["spotdl", "--version"],
                    timeout=5,
                    **kwargs
                )
                if result.returncode == 0:
                    return self._extract_version(result.stdout.strip())
            except:
                pass
        
        return None

    def _extract_version(self, version_string):

        """Extract version number from version string"""

        import re

        match = re.search(r'(\d+\.\d+\.\d+)', version_string)

        return match.group(1) if match else version_string

    def _get_github_assets(self):

        """Get all assets from GitHub releases"""

        try:

            response = requests.get(self.GITHUB_API_LATEST, timeout=10)

            if response.status_code == 200:

                data = response.json()

                assets = data.get("assets", [])

                release_tag = data.get("tag_name", "").lstrip('v')

                return assets, release_tag

        except Exception as e:

            print(f"GitHub API error: {e}")

        

        # Fallback: Try scraping the releases page

        try:

            response = requests.get(self.GITHUB_RELEASES, timeout=10)

            if response.status_code == 200:

                import re

                # Extract assets from HTML

                pattern = r'href="(/spotDL/spotify-downloader/releases/download/[^"]+/([^"]+))"'

                matches = re.findall(pattern, response.text)

                

                assets = []

                for url, filename in matches:

                    assets.append({

                        "name": filename,

                        "browser_download_url": f"https://github.com{url}"

                    })

                

                # Get latest version tag

                tag_pattern = r'/releases/tag/v?(\d+\.\d+\.\d+)'

                tag_matches = re.findall(tag_pattern, response.text)

                release_tag = tag_matches[0] if tag_matches else "4.4.3"

                

                return assets, release_tag

        except Exception as e:

            print(f"GitHub scrape error: {e}")

        

        return [], "4.4.3"

    def _find_matching_asset(self, assets):

        """Find asset matching current platform"""

        import re

        

        if not assets:

            return None

        

        patterns = self.platform_patterns.get(self.current_platform, [])

        

        for asset in assets:

            filename = asset["name"].lower()

            

            for pattern in patterns:

                if re.search(pattern, filename, re.IGNORECASE):

                    return asset

        

        # If no match found, return first executable-like asset

        for asset in assets:

            filename = asset["name"].lower()

            if self.current_platform == "Windows":

                if filename.endswith('.exe'):

                    return asset

            else:

                if not filename.endswith('.exe') and not filename.endswith('.zip') and not filename.endswith('.tar'):

                    return asset

        

        return None

    def get_spotdl_latest_url(self):

        """Get the correct download URL for current platform"""

        assets, version = self._get_github_assets()

        

        if not assets:

            # Fallback to hardcoded URLs with latest known version

            fallback_urls = {

                "Windows": f"https://github.com/{self.GITHUB_REPO}/releases/download/v{version}/spotdl-{version}-win32.exe",

                "Linux": f"https://github.com/{self.GITHUB_REPO}/releases/download/v{version}/spotdl-{version}-linux",

                "Darwin": f"https://github.com/{self.GITHUB_REPO}/releases/download/v{version}/spotdl-{version}-darwin"

            }

            return fallback_urls.get(self.current_platform)

        

        asset = self._find_matching_asset(assets)

        if asset:

            return asset["browser_download_url"]

        

        return None

    # def get_spotdl_status(self):

    #     """Get comprehensive SpotDL status"""

    #     current_version = self.get_spotdl_current_version()
    #     for _ in range(3):
    #         if current_version:
    #             break
    #         time.sleep(1)
    #         current_version = self.get_spotdl_current_version()

    #     latest_url = self.get_spotdl_latest_url()
    #     print(f"Current SpotDL Version: {current_version}")
    #     print(f"Latest SpotDL URL: {latest_url}")

    #     # Extract version from URL if possible
    #     latest_version = "4.4.3"  # Default
    #     if latest_url:
    #         import re
    #         match = re.search(r'/(\d+\.\d+\.\d+)/', latest_url)
    #         if match:
    #             latest_version = match.group(1)

    #     return {
    #         "is_spotdl_downloaded": self.is_spotdl_downloaded(),
    #         "spotdl_current_version": current_version,
    #         "spotdl_latest_version": latest_version,
    #         "spotdl_path": self.get_spotdl_path(),
    #         "spotdl_latest_url": latest_url,
    #         "update_available": self._is_update_available(current_version, latest_version),
    #     }


    # def _is_update_available(self, current, latest):

    #     """Check if update is available"""

    #     if not current:

    #         return False

        

    #     try:

    #         from packaging import version

    #         return version.parse(current) < version.parse(latest)

    #     except:

    #         return current != latest

    # Optional: Add download method like FFmpeg might have

    def download_spotdl(self, callback=None):

        """Download SpotDL executable"""

        url = self.get_spotdl_latest_url()

        if not url:

            return False, "Could not get download URL"

        

        spotdl_path = self.get_spotdl_path()

        

        try:

            # Create backup if exists

            backup_path = None

            if os.path.exists(spotdl_path):

                backup_path = spotdl_path + ".backup"

                shutil.copy2(spotdl_path, backup_path)

            

            # Download with progress

            response = requests.get(url, stream=True, timeout=30)

            response.raise_for_status()

            

            total_size = int(response.headers.get('content-length', 0))

            downloaded = 0

            

            with open(spotdl_path, 'wb') as f:

                for chunk in response.iter_content(chunk_size=8192):

                    if chunk:

                        f.write(chunk)

                        downloaded += len(chunk)

                        

                        if callback and total_size > 0:

                            progress = (downloaded / total_size) * 100

                            callback(progress, downloaded, total_size)

            

            # Make executable on Unix

            if self.current_platform in ["Linux", "Darwin"]:

                os.chmod(spotdl_path, 0o755)

            

            # Verify download

            if os.path.getsize(spotdl_path) < 1024:

                raise Exception("Downloaded file too small")

            

            # Cleanup backup

            if backup_path and os.path.exists(backup_path):

                os.remove(backup_path)

            

            return True, "Download successful"

            

        except Exception as e:

            # Restore backup

            if backup_path and os.path.exists(backup_path):

                if os.path.exists(spotdl_path):

                    os.remove(spotdl_path)

                shutil.move(backup_path, spotdl_path)

            

            return False, str(e)

    def get_spotdl_latest_version(self):
        """Get latest spotdl version from GitHub API"""
        try:
            import requests
            response = requests.get(
                "https://api.github.com/repos/spotDL/spotify-downloader/releases/latest",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()["tag_name"].lstrip("v")
            return None
        except Exception as e:
            print(f"Failed to get latest spotdl version: {e}")
            return None

    def get_spotdl_status(self):
        """Get comprehensive SpotDL status with cross-platform support"""
        
        # Get current version with retry logic
        current_version = self.get_spotdl_current_version()
        for _ in range(3):
            if current_version:
                break
            time.sleep(1)
            current_version = self.get_spotdl_current_version()

        # Get latest download URL
        latest_url = self.get_spotdl_latest_url()

        # Debug logging
        print(f"Current SpotDL Version: {current_version}")
        print(f"Latest SpotDL URL: {latest_url}")
        
        # Extract version from URL if possible
        latest_version = "4.4.3"  # Default fallback version
        if latest_url:
            import re
            # Try to extract version from URL (handles different URL patterns)
            patterns = [
                r'/(\d+\.\d+\.\d+)/',  # /4.4.3/
                r'v(\d+\.\d+\.\d+)',    # v4.4.3
                r'(\d+\.\d+\.\d+)\.exe', # 4.4.3.exe
                r'(\d+\.\d+\.\d+)\.AppImage', # 4.4.3.AppImage
            ]
            
            for pattern in patterns:
                match = re.search(pattern, latest_url)
                if match:
                    latest_version = match.group(1)
                    break
        
        # Check if update is available
        update_available = self._is_update_available(current_version, latest_version)
        
        # Platform-specific executable checks
        spotdl_path = self.get_spotdl_path()
        is_downloaded = self.is_spotdl_downloaded()
        
        # Additional platform-specific validation
        if is_downloaded and platform.system() != "Windows":
            # For Unix-like systems (macOS/Linux), check if executable
            try:
                if not os.access(spotdl_path, os.X_OK):
                    print(f"SpotDL exists but is not executable. Attempting to fix permissions...")
                    os.chmod(spotdl_path, 0o755)
                    print(f"Fixed permissions for {spotdl_path}")
            except Exception as e:
                print(f"Warning: Could not set executable permissions for SpotDL: {e}")
        
        # Return comprehensive status
        return {
            "is_spotdl_downloaded": is_downloaded,
            "spotdl_current_version": current_version,
            "spotdl_latest_version": latest_version,
            "spotdl_path": spotdl_path,
            "spotdl_latest_url": latest_url,
            "update_available": update_available,
            "platform": platform.system(),
            "is_executable": os.access(spotdl_path, os.X_OK) if os.path.exists(spotdl_path) else False,
        }

    def _is_update_available(self, current_version, latest_version):
        """Check if a SpotDL update is available"""
        if not current_version or not latest_version:
            return False
        
        try:
            # Parse version strings
            current_parts = [int(x) for x in current_version.split(".")]
            latest_parts = [int(x) for x in latest_version.split(".")]
            
            # Compare version parts
            for cur, lat in zip(current_parts, latest_parts):
                if lat > cur:
                    return True
                elif lat < cur:
                    return False
            
            # All parts equal
            return len(latest_parts) > len(current_parts)
        except (ValueError, AttributeError):
            return False

    def get_spotdl_path(self):
        """Get cross-platform path to spotdl executable"""
        bin_dir = Path(self.settings.get("bin_dir"))
        
        # Platform-specific executable names
        if platform.system() == "Windows":
            # Windows: .exe extension
            return str(bin_dir / "spotdl.exe")
        elif platform.system() == "Darwin":
            # macOS: typically no extension, could be .app or executable
            # Try common names
            possible_paths = [
                bin_dir / "spotdl",
                bin_dir / "spotdl.app" / "Contents" / "MacOS" / "spotdl",
                bin_dir / "spotdl-macos",
            ]
            for path in possible_paths:
                if path.exists():
                    return str(path)
            # Default fallback
            return str(bin_dir / "spotdl")
        else:
            # Linux/Unix: no extension
            # Try common names
            possible_paths = [
                bin_dir / "spotdl",
                bin_dir / "spotdl.AppImage",
                bin_dir / "spotdl-linux",
            ]
            for path in possible_paths:
                if path.exists():
                    return str(path)
            # Default fallback
            return str(bin_dir / "spotdl")

    def is_spotdl_downloaded(self):
        """Check if spotdl is downloaded to bin folder with platform-specific validation"""
        spotdl_path = self.get_spotdl_path()
        
        if not os.path.exists(spotdl_path):
            return False
        
        # Check file size
        file_size = os.path.getsize(spotdl_path)
        if file_size == 0:
            print(f"Warning: SpotDL file exists but is empty (0 bytes)")
            return False
        
        # Platform-specific validations
        system = platform.system()
        
        if system == "Windows":
            # Windows: check if it's a valid PE executable
            try:
                with open(spotdl_path, 'rb') as f:
                    magic = f.read(2)
                    if magic != b'MZ':
                        print(f"Warning: SpotDL file doesn't appear to be a valid Windows executable")
                        return False
            except Exception:
                pass  # Don't fail if we can't read the file
        
        elif system in ["Darwin", "Linux"]:
            # Unix-like: check if executable or can be made executable
            if not os.access(spotdl_path, os.X_OK):
                # Try to make it executable
                try:
                    os.chmod(spotdl_path, 0o755)
                except Exception as e:
                    print(f"Warning: SpotDL exists but is not executable and cannot be made executable: {e}")
                    return False
        
        return True


class DenoTool:

    LOCAL_FILENAMES_DENO = {

        "Windows": "deno.exe",

        "Linux": "deno",

        "Darwin": "deno",

    }



    GITHUB_API_LATEST = "https://api.github.com/repos/denoland/deno/releases/latest"



    def __init__(self, settings_manager):

        self.settings = settings_manager

        self.current_platform = platform.system()

        self.platform_arch = platform.machine()



    def get_deno_path(self):

        """Get the full path to deno executable"""

        bin_dir = self.settings.get("bin_dir", "bin")

        return str(Path(bin_dir) / self.LOCAL_FILENAMES_DENO[self.current_platform])

    def is_deno_downloaded(self):

        """Check if deno is available"""

        deno_path = self.get_deno_path()

        return os.path.exists(deno_path)

    def get_deno_latest_url(self):

        """Get the url for latest deno version"""

        try:

            response = requests.get(self.GITHUB_API_LATEST, timeout=10)

            if response.status_code == 200:

                data = response.json()

                assets = data.get("assets", [])

                

                platform_identifier = {

                    "Windows": "pc-windows-msvc",

                    "Linux": "unknown-linux-gnu",

                    "Darwin": "apple-darwin"

                }.get(self.current_platform)



                arch_identifier = {

                    "AMD64": "x86_64",

                    "x86_64": "x86_64",

                    "aarch64": "aarch64"

                }.get(self.platform_arch)

                

                if not platform_identifier or not arch_identifier:

                    return None



                for asset in assets:

                    asset_name = asset.get("name", "")

                    if f"{arch_identifier}-{platform_identifier}" in asset_name and asset_name.endswith(".zip"):

                        return asset.get("browser_download_url")

        except Exception as e:

            print(f"GitHub API error for Deno: {e}")

        

        return None

    def get_deno_status(self):

        """Get comprehensive deno status"""

        return {

            "is_deno_downloaded": self.is_deno_downloaded(),

            "deno_path": self.get_deno_path(),

            "deno_latest_url": self.get_deno_latest_url(),

        }

    def get_deno_latest_version(self):
        """Get latest deno version from GitHub API"""
        try:
            import requests
            response = requests.get(
                "https://api.github.com/repos/denoland/deno/releases/latest",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()["tag_name"].lstrip("v")
            return None
        except Exception as e:
            print(f"Failed to get latest deno version: {e}")
            return None
        
    def get_deno_current_version(self):
        """Get the installed Deno version from bin folder only.
        
        Returns:
            str: Deno version string if available, None otherwise
        """
        # Try downloaded version from bin folder
        if self.is_deno_downloaded():  # Checks if file exists in bin folder
            try:
                deno_path = self.get_deno_path()
                
                # Prepare subprocess arguments
                kwargs = {
                    "capture_output": True,
                    "text": True,
                    "timeout": 10,
                }
                
                # Platform-specific process creation flags
                if platform.system() == "Windows":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                elif platform.system() == "Darwin" or platform.system() == "Linux":
                    # Ensure the file is executable
                    if not os.access(deno_path, os.X_OK):
                        os.chmod(deno_path, 0o755)
                
                result = subprocess.run(
                    [deno_path, "--version"],
                    **kwargs
                )
                
                if result.returncode == 0:
                    # Parse version from output (typically "deno 1.43.0")
                    version_output = result.stdout.strip()
                    # Extract version number using regex
                    import re
                    match = re.search(r'deno\s+([\d\.]+)', version_output)
                    if match:
                        return match.group(1)
            except (subprocess.SubprocessError, OSError, TimeoutError) as e:
                print(f"Error getting deno version: {e}")
                return None
            except Exception as e:
                print(f"Unexpected error getting deno version: {e}")
                return None
        
        return None        