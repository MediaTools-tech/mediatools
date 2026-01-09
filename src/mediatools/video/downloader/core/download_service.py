import os
import re
import sys
import time
import subprocess
from pathlib import Path
from mutagen.oggopus import OggOpus
from mutagen.flac import Picture
from mutagen.id3 import PictureType
import tempfile
import platform
from tkinter import messagebox
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, List
import glob
import logging
from datetime import datetime
import threading
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth

# import mimetypes
from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TPE2
from mutagen.mp4 import MP4
import signal
import ctypes
import shutil

import traceback
import json
import inspect

from PIL import Image
import psutil
import base64
import pdb

from threading import Event

TIMEOUT_GRACEFUL = 3  # seconds for graceful termination
TIMEOUT_FORCE = 2  # seconds for force termination
TIMEOUT_CLEANUP = 5  # seconds for cleanup operations
MAX_TERMINATION_ATTEMPTS = 3  # maximum attempts to terminate process

logger = logging.getLogger(__name__)
# Determine platform
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

@dataclass
class DownloadContext:
    """Contains all context needed for downloads"""

    ytdlp_path: str
    ffmpeg_path: str
    ffprobe_path: str
    spotdl_path: str
    cancel_spotdl_event: Event
    ffmpeg_status: Dict[str, bool]
    download_folder: str
    success_frame: Optional[object]  # Reference to success frame in GUI
    progress_bar: object  # Reference to progress bar widget

    # GUI update functions
    update_status: Callable
    update_queue_display: Callable
    gui_after: Callable  # root.after method
    start_queue_processing: Callable

    # Tool update functions
    do_update_yt_dlp: Callable
    do_update_ffmpeg: Callable
    do_update_spotdl: Callable

    # Add state update callbacks
    update_download_state: Optional[Callable] = None
    update_pause_state: Optional[Callable] = None
    update_stop_state: Optional[Callable] = None
    check_internet_connection: Optional[Callable] = None
    add_to_delete_list: Optional[Callable] = None
    pause_resume_disable: Optional[Callable] = None
    check_spotify_credentials_warning: Optional[Callable] = None
    exit_app: Optional[Callable] = None
    hide_spotify_credentials_warning: Optional[Callable] = None

    download_path: str = ""
    download_path_temp: str = ""
    current_process: Optional[Any] = None
    stopdl_process: Optional[Any] = None
    is_downloading: bool = False
    is_stopped: bool = False
    files_downloaded: int = 0
    is_paused: bool = False
    is_resumed: bool = False
    is_exit: bool = False
    is_after_stopped: bool = False
    current_download_url: Optional[str] = None
    paused_url: Optional[str] = None
    safe_title: str = ""
    final_filename_check: Optional[str] = None
    video_index: int = 0
    total_videos: int = 0
    is_playlist: bool = False
    recent_url: str = ""
    status_label_fg: str = ""
    download_type: str = ""
    stopped_downloads_to_be_deleted: List[str] = field(default_factory=list)

class DownloadService:
    """Clean download service with minimal dependencies"""

    def __init__(
        self,
        root,
        queue_manager,
        settings,
        style_manager,
        custom_msg_box,
        context: DownloadContext,
    ):
        self.queue_manager = queue_manager
        self.custom_msg_box = custom_msg_box
        self.context = context
        self.settings = settings
        self.style_manager = style_manager
        self.root = root
        self.percent_value = 0.0
        self.status_text = ""
        self.track_number = 0
        self.is_spotdl_download = False
        self.is_yt_download = False
        self.url_extraction_status = ""
        self.album_name = ""
        self.urls_spotdl = []
        self.last_activity_time = 0
        self.spotify_credentials = False
        self.is_playlist_url = False
        self.total_videos_in_playlist = 0
        self.video_index_in_playlist = 0
        
        try:
            font_config = self.style_manager.get_font_config("button")
            self.button_font = (font_config["family"], font_config["size"])
        except Exception:
            self.button_font = ("Arial", 9)

        try:
            font_config = self.style_manager.get_font_config("label")
            self.label_font = (font_config["family"], font_config["size"])
        except Exception:
            self.label_font = ("Arial", 10)

        try:
            font_config = self.style_manager.get_font_config("messagebox")
            self.messagebox_font = (font_config["family"], font_config["size"])
        except Exception:
            self.messagebox_font = ("Arial", 10)

    @property
    def is_ffmpeg_available(self):
        return self.context.ffmpeg_status["is_ffmpeg_suite_available"]

    @property
    def ffmpeg(self):
        if not self.is_ffmpeg_available:
            return None
        return "ffmpeg" if self.context.ffmpeg_status["is_ffmpeg_suite_installed"] else self.context.ffmpeg_path

    @property
    def ffprobe(self):
        if not self.is_ffmpeg_available:
            return None
        return "ffprobe" if self.context.ffmpeg_status["is_ffmpeg_suite_installed"] else self.context.ffprobe_path

    def download_video(self, url, download_type="video"):
        """
        Prepares and initiates the download for a given URL.
        Acts as a dispatcher to platform-specific handlers.
        """
        if not self.is_ytdlp_downloaded():
            return

        self._prepare_download_context(url, download_type)
        self._update_initial_gui_status(download_type)

        try:
            self._setup_download_paths(url, download_type)
            self._check_ffmpeg_requirements(download_type)

            url_type = self._get_url_type(url)
            if url_type == "spotify":
                self._handle_spotify_download(url, download_type)
            elif url_type == "youtube":
                self._handle_youtube_download(url, download_type)
            else:
                self._handle_generic_download(url, download_type)

        except Exception as e:
            logger.error(f"Download failed for {url}: {e}", exc_info=True)
            self.root.after(
                0, lambda: self.context.update_status("Download failed", error=True)
            )
            self.queue_manager.add_failed_url(url, download_type, "Download failed")
            self.queue_manager.remove_url()
        finally:
            self.context.is_downloading = False
            self.root.after(
                0, self.context.update_queue_display, self.context.status_label_fg
            )

    def _get_url_type(self, url):
        """Determine the type of URL (spotify, youtube, or generic)."""
        lower_url = url.lower()
        if "spotify.com" in lower_url:
            return "spotify"
        if "youtu.be" in lower_url or "youtube.com" in lower_url:
            return "youtube"
        return "generic"

    def _prepare_download_context(self, url, download_type):
        """Resets and prepares the download context for a new download."""
        self.context.is_downloading = True
        self.context.current_download_url = url
        self.context.recent_url = url
        self.context.download_path = ""
        self.context.download_path_temp = ""
        self.context.cancel_spotdl_event.clear()
        
        self.spotify_credentials = False
        self.is_oauth = False
        self.is_spotdl_stopped = False
        self.is_spotdl_paused = False
        self.track_number = 0
        self.is_spotdl_download = False
        self.is_yt_download = False
        self.is_playlist_url = False
        self.total_videos_in_playlist = 0
        self.video_index_in_playlist = 0
        if self.context.hide_spotify_credentials_warning:
            self.context.hide_spotify_credentials_warning()

    def _update_initial_gui_status(self, download_type):
        """Updates the GUI to show that a new download is starting."""
        self.root.after(0, self.context.update_queue_display)
        if self.context.is_resumed:
            status_text = f"Resuming...{self.context.recent_url}"
        else:
            emoji = self.style_manager.get_emoji("find")
            status_text = f"{emoji} Fetching {download_type} info...{self.context.recent_url}"
        
        self.root.after(0, lambda: self.context.update_status(status_text, fg=self.context.status_label_fg))

    def _setup_download_paths(self, url, download_type):
        """Sets up the download and temporary paths for the download."""
        self.context.download_path = self.settings.get("downloads_dir")
        self.context.download_path_temp = os.path.join(self.context.download_path, "temp")
        
        if download_type == "video":
            self.context.download_path = os.path.join(self.context.download_path, "Video")
        else:
            self.context.download_path = os.path.join(self.context.download_path, "Audio")

        if self.settings.get("platform_specific_download_folders"):
            platform_name = ""
            if self.is_spotdl_download:
                platform_name = "spotify"
            else:
                platform_name = self.get_platform_for_downloader(url)

            if platform_name:
                self.context.download_path = os.path.join(self.context.download_path, platform_name)

        os.makedirs(self.context.download_path, exist_ok=True)
        os.makedirs(self.context.download_path_temp, exist_ok=True)

    def _check_ffmpeg_requirements(self, download_type):
        """Checks if FFmpeg is required and warns the user if it's missing."""
        is_mp3 = download_type == "audio" and self.settings.get("audio_format", "m4a") == "mp3"
        is_merged_video = download_type == "video" and self.settings.get("stream_and_merge_format", "bestvideo+bestaudio/best-mkv") != "b"
        
        if not self.is_ffmpeg_available and (is_mp3 or is_merged_video):
            self.status_text = "FFmpeg missing. Some features will be disabled. Download FFmpeg for full functionality."
            self.root.after(
                0,
                lambda: self.context.update_status(
                    self.status_text,
                    percent=0,
                    fg=self.context.status_label_fg,
                    error=True,
                ),
            )
            time.sleep(0.5)

    def _handle_spotify_download(self, url, download_type):
        """Handles the download logic for Spotify URLs."""
        try:
            self.is_spotdl_download = True
            self.context.check_spotify_credentials_warning(url)
            self.fetch_spotify_metadata_and_download(url, download_type)
        except Exception as e:
            self.queue_manager.add_failed_url(url, download_type, "Download failed")
            logger.error(f"Error downloading Spotify URL {url}: {e}", exc_info=True)
        finally:
            self.is_spotdl_download = False

    def _handle_youtube_download(self, url, download_type):
        """Handles the download logic for YouTube URLs."""
        self.is_yt_download = True
        self.is_playlist_url = "list=" in url or "/playlist" in url
        yt_metadata = self.get_yt_metadata(url, self.is_playlist_url)
        
        if not yt_metadata:
            # Fallback to generic download if metadata fetch fails
            self._handle_generic_download(url, download_type)
            return

        tracks = []
        collection_folder = ""
        if self.is_playlist_url:
            collection_folder = f"{yt_metadata['collection_name']} - {yt_metadata['collection_artist']}"
            self.context.download_path = os.path.join(self.context.download_path, self.sanitize_filename(collection_folder))
            os.makedirs(self.context.download_path, exist_ok=True)
            tracks = yt_metadata.get("tracks", [])
            self.total_videos_in_playlist = len(tracks)
        else:
            tracks.append({"youtube_url": url, "file_name": yt_metadata.get('title', 'Unknown')})

        num_of_tracks_skipped = 0
        num_of_tracks_succeeded = 0
        for i, track in enumerate(tracks):
            if self.is_playlist_url:
                self.video_index_in_playlist = i + 1
            youtube_url = track['youtube_url']
            file_name_base = self.sanitize_filename(track['file_name'])
            
            if self._is_file_already_downloaded(file_name_base, download_type):
                self.update_status_skipped(track['file_name'])
                num_of_tracks_skipped += 1
                continue

            if self.download(youtube_url, download_type):
                num_of_tracks_succeeded += 1
                self._post_process_downloaded_file(download_type, file_name_base)
            
        if self.is_playlist_url and (len(tracks) - num_of_tracks_skipped) > 0:
            self.create_m3u_playlist(collection_folder, self.context.download_path)

        self.queue_manager.remove_url()
        if num_of_tracks_succeeded > 0:
            if self.is_playlist_url:
                self.update_status_skipped_count_download_count(num_of_tracks_skipped, len(tracks))
            else:
                self.update_status_download_complete()
        elif len(tracks) > num_of_tracks_skipped:
            self.update_status_download_failed()
        else:
            self.update_status_skipped_count_download_count(num_of_tracks_skipped, len(tracks))
        
        self.is_yt_download = False
            
    def _is_file_already_downloaded(self, file_name_base, download_type):
        """Checks if a file with the given base name already exists."""
        file_ext = self.get_ext(download_type)
        if file_ext:
            file_path_with_ext = os.path.join(self.context.download_path, file_name_base + file_ext)
            if os.path.exists(file_path_with_ext):
                return True
        elif download_type == "audio": # Default for audio is opus
             file_path_with_ext = os.path.join(self.context.download_path, file_name_base + ".opus")
             if os.path.exists(file_path_with_ext):
                return True
        return False

    def _post_process_downloaded_file(self, download_type, file_name_base):
        """Handles post-processing like conversion and renaming."""
        if not self.context.final_filename_check:
            return

        current_file_path = os.path.join(self.context.download_path, self.context.final_filename_check)
        dest_file_path_base = os.path.join(self.context.download_path, file_name_base)

        if download_type == "audio" and self.get_ext(download_type) is None and self.is_ffmpeg_available:
            if current_file_path.endswith(".webm"):
                thumbnail_path = self._find_thumbnail_file(current_file_path)
                valid_opus_file = self.convert_webm_to_opus_safe(current_file_path)
                if valid_opus_file:
                    self.add_thumbnail_to_opus(valid_opus_file, thumbnail_path)
                    final_file_path = self.rename_file_as_per_metadata(valid_opus_file, dest_file_path_base)
                    if final_file_path:
                        self.context.final_filename_check = os.path.basename(final_file_path)
        else:
            final_file_path = self.rename_file_as_per_metadata(current_file_path, dest_file_path_base)
            if final_file_path:
                self.context.final_filename_check = os.path.basename(final_file_path)

    def _handle_generic_download(self, url, download_type):
        """Handles the download for generic URLs."""
        if self.download(url, download_type):
            self.queue_manager.remove_url()
            self.update_status_download_complete()
        else:
            # Failure is already handled in download(), just need to remove from queue
            self.queue_manager.remove_url()

    def is_ytdlp_downloaded(self):
        if not os.path.exists(self.context.ytdlp_path):
            if self.custom_msg_box.custom_askyesno(
                self.root,
                "yt-dlp Missing",
                "yt-dlp is required for downloading videos.\n\nWould you like to download it now?",
                self.messagebox_font,
            ):
                self.context.do_update_yt_dlp()

        if not os.path.exists(self.context.ytdlp_path):
            if self.custom_msg_box.custom_askyesno(
                self.root,
                "yt-dlp Missing",
                "Video downloader cannot proceed without this tool.\n\nPress 'Yes' to download missing yt-dlp\nPress 'No' to exit app",
                self.messagebox_font,
            ):

                return False
            else:
                self.context.exit_app()
        
        return True

    def fetch_spotify_metadata_and_download(self, url, download_type):
        """
        Orchestrates the Spotify download process, deciding whether to use
        API credentials based on settings.
        """
        self.spotify_credentials = bool(self.settings.get("spotify_client_id") and self.settings.get("spotify_client_secret"))
        self.is_oauth = self.settings.get("enable_spotify_playlist", False)

        if self.spotify_credentials:
            self._initialize_spotipy(url)
            self._spotdl_download_with_credentials(url, download_type)
        else:
            self.spotdl_download_without_credentials(url, download_type)

    def _initialize_spotipy(self, url):
        """Initializes the Spotipy client."""
        client_id = self.settings.get("spotify_client_id")
        client_secret = self.settings.get("spotify_client_secret")
        os.environ["SPOTIFY_CLIENT_ID"] = client_id
        os.environ["SPOTIFY_CLIENT_SECRET"] = client_secret

        if self.is_oauth and "/playlist/" in url.lower():
            scope = "playlist-read-private,playlist-read-collaborative"
            redirect_uri = "http://127.0.0.1:8000/callback"
            auth_manager = SpotifyOAuth(
                client_id=client_id, client_secret=client_secret,
                redirect_uri=redirect_uri, scope=scope, cache_path=".spotify_cache"
            )
        else:
            auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        
        self.sp = spotipy.Spotify(auth_manager=auth_manager)

    def _spotdl_download_with_credentials(self, url, download_type):
        """Handles Spotify downloads using credentials for metadata."""
        is_single_track = False
        try:
            collection_id, collection_type, is_single_track = self.process_spotify_url(url)
            if collection_type in ["episode", "show"]:
                self.queue_manager.add_failed_url(url, download_type, "Spotify shows/podcasts not supported")
                self.update_status_download_failed()
                self.queue_manager.remove_url()
                return

            urls_and_metadata = self.check_if_collection_id_json_file_exists(collection_id) if not is_single_track else None
            if not urls_and_metadata:
                urls_and_metadata = self.get_urls_and_metadata(collection_id, collection_type)
                if not is_single_track:
                    self.save_json_file_for_collection_id(collection_id, urls_and_metadata)

            if not urls_and_metadata or not urls_and_metadata.get('tracks'):
                raise Exception("Could not retrieve metadata from Spotify.")

            if not is_single_track:
                collection_name = self.sanitize_filename(urls_and_metadata.get("collection_name", "Spotify_Collection"))
                self.context.download_path = os.path.join(self.context.download_path, collection_name)
                os.makedirs(self.context.download_path, exist_ok=True)
            
            self._process_spotify_tracks_with_credentials(urls_and_metadata, download_type)

        except Exception as e:
            logger.error(f"Spotify download with credentials failed for {url}: {e}", exc_info=True)
            self.queue_manager.add_failed_url(url, download_type, "Download failed")
            self.update_status_download_failed()
        finally:
            self.queue_manager.remove_url()
            self.context.is_downloading = False
            self.is_spotdl_download = False

    def _process_spotify_tracks_with_credentials(self, metadata, download_type):
        """Processes and downloads a list of Spotify tracks with metadata."""
        tracks = metadata.get('tracks', [])
        self.total_videos_in_playlist = len(tracks)
        if self.total_videos_in_playlist > 1:
            self.is_playlist_url = True
        collection_name = metadata.get('collection_name', '')
        collection_artist = metadata.get('collection_artist', '')
        tracks_downloaded = 0
        tracks_skipped = 0

        for i, track in enumerate(tracks):
            self.video_index_in_playlist = i + 1
            if self.context.cancel_spotdl_event.is_set():
                return

            file_name_base = self.sanitize_filename(track['file_name'])
            
            if self._is_file_already_downloaded(file_name_base, download_type):
                self.update_status_skipped(track['file_name'])
                tracks_skipped += 1
                continue

            yt_url = self._get_youtube_url_for_spotify_track(track, collection_name, download_type)
            if not yt_url:
                logger.warning(f"Could not find YouTube URL for Spotify track: {track.get('title')}")
                continue

            if self.download(yt_url, download_type):
                tracks_downloaded += 1
                self._post_process_downloaded_file(download_type, file_name_base)
                
                final_file_path = os.path.join(self.context.download_path, self.context.final_filename_check)
                if os.path.exists(final_file_path):
                    artist = collection_artist or track.get('artist', '')
                    self.inject_track_metadata(final_file_path, track, collection_name, artist)
            
            time.sleep(self.settings.get("sleep_interval_between_downloads", 5))

        if tracks_downloaded > 0:
            self.update_status_skipped_count_download_count(tracks_skipped, len(tracks))
        elif len(tracks) > tracks_skipped:
            self.update_status_download_failed()
        else:
            self.update_status_skipped_count_download_count(tracks_skipped, len(tracks))
        
        if tracks_downloaded > 0 and collection_name and len(tracks) > 1:
            self.create_m3u_playlist(collection_name, self.context.download_path)

    def _get_youtube_url_for_spotify_track(self, track, collection_name, download_type):
        """Finds a corresponding YouTube URL for a Spotify track."""
        spotify_url = track.get('spotify_url')
        if not spotify_url:
            return None

        # Prioritize spotdl for audio, yt-search for video
        if download_type == "audio":
            yt_url = self.spotdl_convert_spoti_to_yt_url(spotify_url)
            if not yt_url:
                yt_url = self.get_ytserach_url(collection_name, track)
        else: # video
            yt_url = self.get_ytserach_url(collection_name, track)
            if not yt_url:
                yt_url = self.spotdl_convert_spoti_to_yt_url(spotify_url)
        
        return yt_url
        
    def check_if_collection_id_json_file_exists(self, collection_id):
        """Load Spotify metadata from file for pause/resume capability"""
        json_file_folder = self.settings.get("data_dir")
        
        # Ensure folder exists
        if not os.path.exists(json_file_folder):
            return None

        file_path = os.path.join(json_file_folder, f"{collection_id}.json")
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"Loaded metadata for: {collection_id}")
                return data
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading metadata file: {e}")
                return None
        
        return None

    def save_json_file_for_collection_id(self, collection_id, urls_and_metadata):
        """Save Spotify metadata to file, keep only latest 10 files"""
        MAX_JSON_FILES = 20
        json_file_folder = self.settings.get("data_dir")
        
        # Ensure folder exists
        os.makedirs(json_file_folder, exist_ok=True)
        
        # First, enforce 10-file limit using your direct method
        files = []
        for f in glob.glob(os.path.join(json_file_folder, "*.json")):
            filename = os.path.basename(f)
            if filename != "settings.json" and len(filename.replace('.json', '')) >= 22:
                files.append(f)

        if len(files) >= MAX_JSON_FILES:
            oldest_file = min(files, key=os.path.getmtime)
            try:
                os.remove(oldest_file)
                print(f"Removed: {os.path.basename(oldest_file)}")
            except OSError as e:
                print(f"Error removing {oldest_file}: {e}")

        # Save the new file
        file_path = os.path.join(json_file_folder, f"{collection_id}.json")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(urls_and_metadata, f, ensure_ascii=False, indent=2)
            print(f"Saved metadata for: {collection_id}")
            return True
        except IOError as e:
            print(f"Error saving metadata file: {e}")
            return False


    def spotdl_convert_spoti_to_yt_url(self, spoti_url):
        """COnvert spotify url to yt url"""
        try:
            yt_url = ""
            cmd = [
                self.context.spotdl_path, "url", spoti_url,
                "--threads", "1",
                "--max-retries", "10",
                "--use-cache-file",
                "--cache-path", "./spotdl_cache"
            ]

            process_kwargs = {
                "capture_output": True,
                "text": True,
                "timeout": 120,
                "encoding": 'utf-8',
                "errors": 'replace',
                "env": os.environ
            }

            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                cmd, 
                **process_kwargs
            )

            if result.returncode != 0:
                print(f"spotdl failed with error: {result.stderr}")
                return None
            else:
                # import re
                url_pattern = r'https?://(?:www\.)?(?:music\.)?youtube\.com/watch\?[^\s]*v=[\w-]+[^\s]*|https?://youtu\.be/[\w-]+[^\s]*'
                match = re.search(url_pattern, result.stdout)
                if match:
                    yt_url = match.group(0)
                else:
                    all_urls = re.findall(r'https?://[^\s]+', result.stdout)
                    for url in reversed(all_urls):  # Check from end to start
                        if 'youtube.com' in url or 'youtu.be' in url:
                            yt_url = url
                            break
                
                if yt_url:
                    # print(f"Found YouTube URL: {yt_url}")
                    pass
                else:
                    print(f"No YouTube URL found. Full output:\n{result.stdout}")

                self.status_text = f"Downloading track {yt_url}"
                self.root.after(
                    0,
                    lambda: self.context.update_status(
                        self.status_text,
                        percent=self.percent_value,
                        fg=self.context.status_label_fg,
                    ),
                )

            return yt_url
        
        except:
            print("spotdl_convert_spoti_to_yt_url() failed to convert url")
            return None

    def spotdl_download_without_credentials(self, url, download_type):
        """ Try approach 2 mentioned in doc string, without credentials """
        self.url_extraction_status = ""
        self.album_name = ""
        self.urls_spotdl = []
        self.is_spotdl_download = True
        self.is_playlist_url = True
        is_full_playlist_done = False
        valid_opus_file = ""
        thumbnail_path = ""

        file_ext = self.get_ext(download_type)

        self.status_text = f"Extracting album/playlist URLs..."
        self.root.after(
            0,
            lambda: self.context.update_status(
                self.status_text,
                percent=0,
                fg=self.context.status_label_fg,
            ),
        )

        self.album_name = ""
        self.urls_spotdl = []
        self.url_extraction_status = "running"

        extraction_thread = threading.Thread(
            target=self._extract_spotdl_urls,
            args=(url, download_type,),
            daemon=True
        )
        extraction_thread.start()

        already_downloaded_tracks = []
        last_activity = time.time()
        self.last_activity_time = 0
        prev_value = 0
        while self.url_extraction_status in ["running", "done"]: # break on "complete"
            if self.context.cancel_spotdl_event.is_set():
                return

            if self.context.stopdl_process is None:
                time.sleep(2)
                continue
            self.last_activity_time += time.time() - last_activity
            last_activity = time.time()
            # print(f"while loop last_activity_time: {self.last_activity_time:.1f}s")
            if self.last_activity_time >= (prev_value+5):
                # print(f"Inside while looplast_activity_time: {self.last_activity_time:.1f}s")
                prev_value = self.last_activity_time
            if self.last_activity_time > 900:
                print("No activity detected for 15 minutes, assuming stalled. Exiting extraction loop.")
                self.url_extraction_status = "No activity detected for 15 minutes. Exiting extraction loop. Try using credentials."
                self.queue_manager.add_failed_url(url, download_type, "Download failed")
                self.update_status_download_failed()
                self.queue_manager.remove_url()
                if self.context.stopdl_process:
                    try:
                        self.stop_download_core(self.context.stopdl_process)
                    except Exception as e:
                        print(f"Error terminating process: {e}")
                return
            # if (self.album_name and self.urls_spotdl):
            if (self.urls_spotdl):
                if self.album_name and not hasattr(self, '_folder_created'):
                    self.album_name = re.sub(r'[^\w\s\-]', '', str(self.album_name)).strip()
                    self.context.download_path = os.path.join(self.context.download_path, self.album_name)
                    os.makedirs(self.context.download_path, exist_ok=True)
                    self._folder_created = True
                    
                # Process new URLs (thread-safe iteration)
                urls_to_process = self.urls_spotdl.copy()  # ← Copy to avoid race conditions                                
                for spotdl_url in urls_to_process:
                    if self.context.cancel_spotdl_event.is_set():
                        return
                    if spotdl_url not in already_downloaded_tracks:
                        self.context.is_downloading = True
                        self.video_index_in_playlist = self.track_number + 1
                        print(f"urls_to_process: {urls_to_process}")
                        self.status_text = f"Downloading track {self.track_number} - {spotdl_url}"
                        self.root.after(
                            0,
                            lambda: self.context.update_status(
                                self.status_text,
                                percent=self.percent_value,
                                fg=self.context.status_label_fg,
                            ),
                        )
                        self.download(spotdl_url, download_type)

                        if self.context.final_filename_check and download_type == "audio" and \
                            file_ext is None and self.is_ffmpeg_available:
                            current_file_name = os.path.join(self.context.download_path, self.context.final_filename_check)
                            if current_file_name and current_file_name.endswith(".webm"):
                                thumbnail_path = self._find_thumbnail_file(current_file_name)
                                valid_opus_file = self.convert_webm_to_opus_safe(current_file_name)
                                # self.context.final_filename_check = os.path.basename(valid_opus_file)
                                if valid_opus_file:
                                    self.add_thumbnail_to_opus(valid_opus_file, thumbnail_path)
                                    # No metadta avaialble here
                                    # file_name_final = self.rename_file_as_per_metadata(file_name_final)
                                    self.context.final_filename_check = os.path.basename(valid_opus_file)

                        self.track_number += 1
                        already_downloaded_tracks.append(spotdl_url)
                    elif already_downloaded_tracks == self.urls_spotdl and self.url_extraction_status == "done":
                        self.url_extraction_status = "exit"
                        self.queue_manager.remove_url()
                        self.update_status_download_complete()
                        self.context.is_downloading = False
                        self.is_spotdl_download = False
                        if (self.album_name):
                            self.create_m3u_playlist(self.album_name, self.context.download_path)
                        break
                    else:
                        time.sleep(2)
            time.sleep(2)

        if already_downloaded_tracks != self.urls_spotdl or self.url_extraction_status == "error":
            self.queue_manager.add_failed_url(url, download_type, "Download failed")
            self.queue_manager.remove_url()
            self.update_status_download_failed()
            return

        if hasattr(self, '_folder_created'):
            del self._folder_created

    def convert_webm_to_opus_safe(self, webm_path):
        """
        Convert a .webm audio file (containing Opus) to .opus losslessly.
        Returns the path to the output .opus file.
        Raises RuntimeError on failure.
        """
        if not os.path.isfile(webm_path):
            raise FileNotFoundError(f"Input file not found: {webm_path}")

        base_name = os.path.splitext(os.path.basename(webm_path))[0]
        opus_path = os.path.join(os.path.dirname(webm_path), f"{base_name}.opus")

        # First attempt: lossless stream copy
        cmd_copy = [
            self.ffmpeg,
            "-hide_banner",
            "-y",
            "-i", webm_path,
            "-vn",              # no video
            "-c:a", "copy",     # stream copy audio
            opus_path
        ]

        try:
            process_kwargs = {
                "capture_output": True,
                "text": True,
                "check": False
            }

            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                
            result = subprocess.run(cmd_copy, **process_kwargs)
            
            # Even with the parsing warning, it often succeeds
            if result.returncode == 0 and os.path.isfile(opus_path) and os.path.getsize(opus_path) > 1000:
                logger.info(f"Lossless conversion succeeded: {opus_path}")
                return opus_path
            
            # If copy failed meaningfully, fall back to re-encode
            logger.warning(f"Stream copy failed (returncode {result.returncode}). Falling back to re-encode.")
            logger.debug(result.stderr)

        except Exception as e:
            print(e)
            logger.error(f"Error during stream copy: {e}")


    def rename_file_as_per_metadata(self, src_file, dest_file):
        """Rename file function"""
        """dest_file must be full file path without ext"""
        try:
            ext = src_file.rsplit(".")[-1]
            file_final_name = dest_file + f".{ext}"
            if os.path.exists(src_file) and not os.path.exists(file_final_name):
                os.rename(src_file, file_final_name)
            if os.path.exists(file_final_name):
                return file_final_name
            elif os.path.exists(src_file):
                return src_file
        except:
            return None

    def inject_track_metadata(self, file_path, track_info, album_name, album_artist):
        """
        Inject metadata into a single audio file (M4A, MP3, or WEBM).
        
        Args:
            file_path: Full path to the audio file
            track_info: Dict with track metadata (title, artist, track_number)
            album_name: Name of the album
            album_artist: Main album artist
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext in ['.m4a', '.mp4']:
                return self._inject_m4a_metadata(file_path, track_info, album_name, album_artist)
            elif file_ext == '.mp3':
                return self._inject_mp3_metadata(file_path, track_info, album_name, album_artist)
            elif file_ext == '.opus':
                return self._inject_opus_metadata(file_path, track_info, album_name, album_artist)
            else:
                print(f"⚠️ Unsupported format: {file_ext} (only M4A, MP3, WEBM supported)")
                return False
        except Exception as e:
            print(f"💥 Error processing {os.path.basename(file_path)}: {e}")
            return False

    def _inject_m4a_metadata(self, file_path, track, album_name, album_artist):
        """Inject metadata into M4A/MP4 files."""
        try:
            audio = MP4(file_path)
            
            # M4A uses specific tag names
            audio['\xa9nam'] = track.get('title', 'Unknown Title')      # Title
            audio['\xa9ART'] = track.get('artist', 'Unknown Artist')    # Artist
            audio['\xa9alb'] = album_name                               # Album
            audio['aART'] = album_artist                                # Album Artist
            audio['trkn'] = [(track.get('track_number', 0), 0)]         # Track number
            
            audio.save()
            return True
        except Exception as e:
            print(f"M4A Error: {e}")
            return False

    def _inject_mp3_metadata(self, file_path, track, album_name, album_artist):
        """Inject metadata into MP3 files."""
        try:
            # Try to load existing ID3 tags
            try:
                audio = EasyID3(file_path)
            except:
                # Create new tags if none exist
                audio = EasyID3()
            
            # Set basic metadata
            audio['title'] = track.get('title', 'Unknown Title')
            audio['artist'] = track.get('artist', 'Unknown Artist')
            audio['album'] = album_name
            audio['albumartist'] = album_artist
            audio['tracknumber'] = str(track.get('track_number', 0))
            
            # Save the EasyID3 tags
            audio.save(file_path)
            
            # Add album artist separately (not always in EasyID3)
            try:
                id3 = ID3(file_path)
                id3.add(TPE2(encoding=3, text=album_artist))
                id3.save()
            except:
                pass  # Album artist already saved or not critical
            
            return True
        except Exception as e:
            print(f"MP3 Error: {e}")
            return False

    def _inject_opus_metadata(self, file_path, track, album_name, album_artist):
        """
        Inject metadata into OGG/Opus (.opus) files.
        Works reliably with OGG container's Vorbis comment system.
        """
        try:
            # Load the Opus file
            audio = OggOpus(file_path)
            
            # Set core metadata (Vorbis comment format)
            audio['title'] = track.get('title', 'Unknown Title')
            audio['artist'] = track.get('artist', 'Unknown Artist')
            audio['album'] = album_name
            audio['albumartist'] = album_artist
            
            # Track number
            track_num = track.get('track_number', 0)
            if track_num:
                audio['tracknumber'] = str(track_num)
            
            # Optional: Add other common tags
            if 'genre' in track:
                audio['genre'] = track['genre']
            
            if 'date' in track or 'year' in track:
                year = track.get('date') or track.get('year')
                if year:
                    audio['date'] = str(year)
            
            # Save the metadata
            audio.save()
            
            # Verify it worked
            # saved_title = audio.get('title', [''])[0]
            # saved_artist = audio.get('artist', [''])[0]
            return True
            
        except ImportError:
            print("❌ Need: pip install mutagen[oggopus]")
            return False
            
        except Exception as e:
            print(f"❌ OGG/Opus metadata error: {type(e).__name__}: {e}")
            
            # Fallback: Try FFmpeg if mutagen fails
            return self._inject_opus_metadata_ffmpeg_fallback(
                file_path, track, album_name, album_artist
            )

    def _inject_opus_metadata_ffmpeg_fallback(self, file_path, track, album_name, album_artist):
        """FFmpeg fallback for problematic Opus files."""

        temp_output = tempfile.mktemp(suffix='.opus')
        
        cmd = [
            self.ffmpeg,
            '-i', file_path,
            '-metadata', f'title={track.get("title", "")}',
            '-metadata', f'artist={track.get("artist", "")}',
            '-metadata', f'album={album_name}',
            '-metadata', f'album_artist={album_artist}',
            '-metadata', f'track={track.get("track_number", 0)}',
            '-c:a', 'copy',  # Copy Opus audio (no transcode)
            '-y', temp_output
        ]
        
        try:
            process_kwargs = {
                "capture_output": True,
                "text": True
            }

            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                
            result = subprocess.run(cmd, **process_kwargs)
            
            if result.returncode == 0:
                # Replace original
                # import shutil
                shutil.move(temp_output, file_path)
                print(f"✅ OGG/Opus metadata via FFmpeg fallback")
                return True
            else:
                print(f"❌ FFmpeg fallback failed: {result.stderr[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ FFmpeg error: {e}")
            return False
        finally:
            # Cleanup
            if os.path.exists(temp_output):
                os.remove(temp_output)

    def get_ytserach_url(self, collection_name, track_data):
        yt_url = None
        search_query = f"Title - {track_data['title']}, Artist - {track_data['artist']}, Album - {track_data['album']}, Collection - {collection_name}"
        search_query = track_data['title']
        if track_data['artist']:
            search_query += f" - {track_data['artist']}"
        elif track_data['album']:
            search_query += f" - {track_data['album']}"
        elif track_data['collection_name']:
            search_query += f" - {track_data['collection_name']}"
        
        cmd = [
            self.context.ytdlp_path, 
            f'ytsearch1:{search_query}',
            '--print', 'webpage_url',
            '--format', 'bestaudio'
        ]
        try:
            process_kwargs = {
                "capture_output": True,
                "text": True,
                "timeout": 30 # Added timeout for consistency
            }

            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                
            result = subprocess.run(cmd, **process_kwargs)
            yt_url = result.stdout.strip()
            return yt_url
        except:
            return None

    def get_platform_for_downloader(self, url):
        """Optimized for video/audio downloader apps"""

        if 'youtube' in url.lower() or 'youtu.be' in url.lower():
            return 'youtube'
        elif 'spotify' in url.lower():
            return 'spotify'
        else:
            try:
                return self.get_platform(url)
            except:
                return 'other'

    def get_platform(self, url):
        """
        Extract platform from URL using rsplit
        SIMPLE, NO DEPENDENCIES, WORKS 100%
        """
        # Clean: remove protocol, path, port
        if '://' in url:
            url = url.split('://', 1)[1]
        
        domain = url.split('/')[0].split(':')[0]
        
        # Handle all cases with simple logic
        parts = domain.split('.')
        
        if len(parts) == 1:
            return parts[0]  # No dots
        
        # For 2+ parts, get the meaningful middle part
        if len(parts) == 2:
            return parts[0]  # example.com
        
        # For 3+ parts, need to skip subdomains and TLD parts
        # Common subdomains to skip
        skip_first = {'www', 'm', 'mobile', 'api', 'open', 'music'}
        
        # Common TLD parts to check
        tld_parts = {'co', 'com', 'org', 'net'}
        
        # Start from position 1 (skip first if it's a subdomain)
        start = 1 if parts[0] in skip_first else 0
        
        # Check if we have a country TLD pattern
        if len(parts) - start >= 3 and parts[start+1] in tld_parts:
            return parts[start]  # youtube.co.uk
        
        return parts[start]  # www.youtube.com
    
    def _extract_spotdl_urls(self, url, download_type):
        """Extract collection name from Spotify URL"""
        process_exited_normally = False
        try:
            cmd = [
                self.context.spotdl_path, "url", url,
                "--threads", "1",  # Low threads = low rate risk
                "--max-retries", "10",
                "--use-cache-file"
                # "--log-level", "WARNING"
            ]

            process_kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "bufsize": 1,
                "universal_newlines": True,
                "encoding": "utf-8",
                "errors": "replace",
                "start_new_session": True,
            }

            # Add platform-specific window hiding
            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

                # Optional: Additional window hiding for extra reliability
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                process_kwargs["startupinfo"] = startupinfo

            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(cmd, **process_kwargs, env=os.environ)
            # process = subprocess.Popen(cmd, **process_kwargs)
            # process = subprocess.Popen(cmd, **process_kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, env=os.environ)
            self.context.stopdl_process = process

            rate_hits = 0
            retry_attempted = False

            for line in process.stdout:
                if self.context.cancel_spotdl_event.is_set():
                    return
                
                # Check if process has been terminated externally
                if self.context.stopdl_process.poll() is not None:
                    print("Process terminated externally")
                    break

                line = line.strip()
                self.last_activity_time = 0

                if "found" in line.lower() and "songs in" in line.lower():
                    match = re.search(r"found\s+(\d+)\s+songs", line.lower())
                    if match:
                        self.total_videos_in_playlist = int(match.group(1))
                    if not self.album_name:
                        self.album_name = line.split("songs in", 1)[1].strip()
                # Check for YouTube URLs
                if ("youtube.com" in line.lower() or "youtu.be" in line.lower()) and "http" in line.lower():
                    url_match = re.search(r'https?://\S+', line)
                    if url_match:
                        url_in_line = url_match.group(0).rstrip('.,;:)')
                        self.urls_spotdl.append(url_in_line.strip())
                if "rate limit" in line.lower() or "429" in line or "rate/request limit" in line.lower() or "Retry will occur after" in line.lower():
                    rate_hits += 1
                    restart_delay = 300
                    print(f"RATE LIMIT #{rate_hits} DETECTED!")  # Or emit GUI signal
                    if rate_hits >= 10:
                        print("Too many rate limit hits, aborting extraction.")
                        self.context.stopdl_process.terminate()
                        self.context.stopdl_process.wait()
                        if self.context.stopdl_process:
                            self.stop_download_core(self.context.stopdl_process)
                        if not retry_attempted:
                            self.status_text = f"Rate limited, retrying extraction after {restart_delay}s..."
                            self.root.after(
                                0,
                                lambda: self.context.update_status(
                                    self.status_text,
                                    percent=0,
                                    fg=self.context.status_label_fg,
                                ),
                            )
                            time.sleep(restart_delay)
                            process = subprocess.Popen(cmd, **process_kwargs)
                            self.context.stopdl_process = process
                            retry_attempted = True
                        else:
                            self.status_text = "Extraction failed due to repeated rate limiting."
                            self.root.after(
                                0,
                                lambda: self.context.update_status(
                                    self.status_text,
                                    percent=0,
                                    fg=self.context.status_label_fg,
                                ),
                            )
                            self.queue_manager.add_failed_url(url, download_type, "Download failed")
                            print("Retry already attempted, not retrying again.")
                            self.stop_download_core(process)
                            break

            # Wait for completion and handle exit codes properly
            return_code = self.context.stopdl_process.wait()

            if return_code == 0:
                print("Success")
                self.url_extraction_status = "done"
                process_exited_normally = True
                return
    
            else:
                print(f"SpotDL failed with code {return_code}. Check logs.")
                self.url_extraction_status = "error"
                process_exited_normally = False
                return

        except subprocess.TimeoutExpired:
            print("SpotDL timed out—killing process.")
            self.url_extraction_status = "error"
            process_exited_normally = False
            return
        finally:
            if not process_exited_normally:
                self._cleanup_extraction_process()  # Move to separate method

    def _cleanup_extraction_process(self):
        """Safely clean up extraction process"""
        if not hasattr(self.context, 'stopdl_process') or not self.context.stopdl_process:
            return
        
        try:
            # Check if process is actually running
            if self.context.stopdl_process.poll() is None:
                print("Terminating running process...")
                self.stop_download_core(self.context.stopdl_process)
            else:
                print("Process already finished")
        except Exception as e:
            print(f"Cleanup warning: {e}")
        finally:
            # Always clear reference
            self.context.stopdl_process = None

    def terminate_process_minimal_version(self, process):
        """Terminate process"""
        # Use communicate with the timeout, which attempts to kill the process on expiration
        if sys.platform == "win32":
            # For Windows, use taskkill command to kill process and its children (/T /F)
            process_kwargs = {}
            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            # For POSIX, kill the entire process group by sending a signal to the negative PGID
            os.killpg(process.pid, signal.SIGTERM)
            
        # Re-raise the exception after cleanup
        raise

    def create_m3u_playlist(self, collection_name, download_folder):
        """
        Create an M3U playlist file from downloaded media files (audio and video).
        Robust handling of missing data and file detection.
        
        Args:
            collection_name: Collection name (string or None)
            download_folder: Path to folder with media files
        
        Returns:
            Path to created playlist or None if no files found
        """
        try:
            # Ensure download folder exists
            download_folder = Path(download_folder)
            if not download_folder.exists():
                print(f"Download folder doesn't exist: {download_folder}")
                return None
            
            # Get all media files (audio and video)
            media_extensions = [
                # Audio formats
                '*.mp3', '*.m4a', '*.flac', '*.wav', '*.ogg', '*.opus', '*.aac', '*.wma',
                # Video formats  
                '*.mp4', '*.mkv', '*.avi', '*.mov', '*.wmv', '*.flv', '*.webm', '*.m4v',
                '*.mpeg', '*.mpg', '*.3gp', '*.ts', '*.mts', '*.vob'
            ]
            
            media_files = []
            for ext in media_extensions:
                media_files.extend(download_folder.glob(ext))
            
            # Check if any files found
            if not media_files:
                print(f"No media files found in: {download_folder}")
                return None
            
            # print(f"Found {len(media_files)} media files")
            
            # Sort files naturally (handles track numbers correctly)
            def natural_sort_key(path):
                """Sort key that handles numbers naturally (1, 2, 10 not 1, 10, 2)"""
                parts = re.split(r'(\d+)', path.name.lower())
                return [int(p) if p.isdigit() else p for p in parts]
            
            media_files.sort(key=natural_sort_key)
            
            # Create playlist name
            if collection_name:
                playlist_name = str(collection_name).strip()
            else:
                playlist_name = download_folder.name
            
            # Clean filename (remove invalid characters)
            def sanitize_filename(name):
                """Remove invalid filename characters"""
                invalid_chars = '<>:"/\\|?*'
                for char in invalid_chars:
                    name = name.replace(char, '_')
                name = name.rstrip('. ')  # Windows can't end with dot/space
                return ' '.join(name.split())[:100]  # Remove extra spaces and limit
            
            playlist_name = sanitize_filename(playlist_name)
            if not playlist_name:
                playlist_name = "Playlist"
            
            playlist_path = download_folder / f"{playlist_name}.m3u"
            
            # Helper function to get duration from file (optional)
            def get_duration_from_file(filepath):
                """Try to get duration from file using ffprobe if available"""
                try:
                    cmd = [
                        'ffprobe',
                        '-v', 'quiet',
                        '-show_entries', 'format=duration',
                        '-of', 'json',
                        str(filepath)
                    ]
                    import subprocess
                    process_kwargs = {
                        "capture_output": True,
                        "text": True
                    }

                    if IS_WINDOWS:
                        process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                        
                    result = subprocess.run(cmd, **process_kwargs)
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        duration = float(data['format']['duration'])
                        return int(duration)  # Return as integer seconds
                except:
                    pass
                return 0  # Default if can't get duration
            
            # Create M3U content
            m3u_lines = ["#EXTM3U"]
            m3u_lines.append(f"#PLAYLIST:{playlist_name}")
            m3u_lines.append("")
            
            # Add each media file
            for media_file in media_files:
                # Get duration (optional, can be 0 if not available)
                duration = get_duration_from_file(media_file)
                
                # Title = filename without extension
                title = media_file.stem
                
                # Add EXTINF line with duration and title
                m3u_lines.append(f"#EXTINF:{duration},{title}")
                
                # Add filename (relative to playlist location)
                m3u_lines.append(media_file.name)
                m3u_lines.append("")
            
            # Remove last empty line if present
            if m3u_lines[-1] == "":
                m3u_lines.pop()
            
            # Write to file with error handling
            try:
                with open(playlist_path, 'w', encoding='utf-8', errors='replace') as f:
                    f.write('\n'.join(m3u_lines))
                
                return str(playlist_path)
                
            except Exception as e:
                print(f"Failed to write playlist file: {e}")
                return None
                
        except Exception as e:
            print(f"Error creating playlist: {e}")
            traceback.print_exc()
            return None

    def get_yt_metadata(self, url, is_playlist):
        """Get metadata fields"""
        
        if is_playlist:
            try:
                cmd = [
                    self.context.ytdlp_path, 
                    url, 
                    "--flat-playlist", 
                    "--dump-single-json"
                ]

                process_kwargs = {
                    "capture_output": True,
                    "text": True,
                    "timeout": 60,
                    "encoding": 'utf-8',
                    "errors": 'replace'
                }

                if IS_WINDOWS:
                    process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

                if IS_WINDOWS:
                    process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

                result = subprocess.run(
                    cmd,
                    **process_kwargs
                )
                
                if result.returncode == 0:
                    try:
                        data = json.loads(result.stdout)
                        
                        # Build result structure
                        result_metadata = {
                            'collection_type': 'youtube_playlist',
                            'collection_id': data.get('id', ''),
                            'collection_name': (
                                data.get("title") or 
                                data.get("playlist_title") or 
                                data.get("playlist") or 
                                "YouTube_Playlist"
                            ),
                            'collection_artist': data.get('uploader', ''),
                            'tracks': [],
                            'total_tracks': 0
                        }
                        
                        # Extract track entries
                        entries = data.get('entries', [])
                        if entries:
                            for idx, entry in enumerate(entries, 1):
                                if entry:  # Skip None entries (deleted videos)
                                    track_data = {
                                        'youtube_url': f"https://youtube.com/watch?v={entry.get('id', '')}",
                                        'title': entry.get('title', f'Track {idx}'),
                                        'artist': entry.get('uploader', ''),
                                        'album': result_metadata['collection_name'],
                                        'track_number': idx,
                                        'file_name': f"{idx:02d} - {entry.get('title', f'Track {idx}')}",
                                        'album_artist': result_metadata['collection_artist'],
                                        'duration_ms': int(entry.get('duration', 0) * 1000) if entry.get('duration') else 0
                                    }
                                    result_metadata['tracks'].append(track_data)
                            
                            result_metadata['total_tracks'] = len(result_metadata['tracks'])
                        
                        return result_metadata
                        
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSON from yt-dlp: {e}")
                        print(f"Raw output: {result.stdout[:200]}...")
                        
            except subprocess.TimeoutExpired:
                print("yt-dlp timed out while extracting playlist metadata")
            except Exception as e:
                print(f"Error extracting playlist metadata: {e}")
                import traceback
                traceback.print_exc()
        else:
            try:
                cmd = [
                    self.context.ytdlp_path,
                    '--no-playlist',
                    '--print', '%(title)s|||%(uploader)s|||%(s)s',
                    '--quiet',
                    url
                ]
                
                process_kwargs = {
                    "capture_output": True,
                    "text": True,
                    "timeout": 30
                }

                if IS_WINDOWS:
                    process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

                if IS_WINDOWS:
                    process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                
                result = subprocess.run(cmd, **process_kwargs)
                
                if result.returncode == 0:
                    parts = result.stdout.strip().split('|||')
                    return {
                        'title': parts[0] if len(parts) > 0 else None,
                        'artist': parts[1] if len(parts) > 1 else None,
                        'duration': parts[2] if len(parts) > 2 else None
                    }
                
                return None
                
            except Exception as e:
                return None

    def sanitize_filename(self, title):
        # Allow: alphanumeric, space, hyphen, underscore, dot, parentheses, ampersand
        # Adjust the regex pattern to include any other safe characters you want
        title = re.sub(r'[^\w\s\-\.\(\)&]', '', title)  # Keep only whitelisted chars
        title = re.sub(r'\s+', ' ', title).strip()      # Collapse multiple spaces
        title = title.rstrip(' .') # Strip trailing dots and spaces
        return title[:250]  # Limit length

    def get_ext(self, download_type):
        if download_type == "audio":
            file_ext = self.settings.get("audio_format", "m4a")
            if file_ext == "m4a":
                return ".m4a"
            elif file_ext == "mp3":
                return ".mp3"
            else:
                return None

        if download_type == "video":
            file_ext = self.settings.get("stream_and_merge_format", "bestvideo+bestaudio/best-mkv")
            if file_ext == "bestvideo+bestaudio/best-mkv":
                return ".mkv"
            elif file_ext == "bestvideo+bestaudio/best-mp4":
                return ".mp4"
            else:
                return None

    def update_status_download_failed(self):
        self.root.after(
            0,
            self.context.update_queue_display(fg=self.context.status_label_fg),
        )
        self.status_text = f"{self.style_manager.get_emoji('error')} Download Failed!."
        self.root.after(
            0,
            lambda: self.context.update_status(
                self.status_text,
                percent=0,
                fg=self.context.status_label_fg,
                error=True
            ),
        )

    def update_status_download_complete(self):
        self.root.after(
            0,
            self.context.update_queue_display(fg=self.context.status_label_fg),
        )
        self.status_text = f"✓ Download complete."
        self.root.after(
            0,
            lambda: self.context.update_status(
                self.status_text,
                percent=0,
                fg=self.context.status_label_fg,
            ),
        )

    def update_status_skipped_count_download_count(self, skipped_count, total_count):
        self.root.after(
            0,
            self.context.update_queue_display(fg=self.context.status_label_fg),
        )
        self.status_text = f"✓ Download complete.   Duplicate tracks skipped {skipped_count},   Downloaded {total_count-skipped_count},   Out of {total_count}"
        self.root.after(
            0,
            lambda: self.context.update_status(
                self.status_text,
                percent=0,
                fg=self.context.status_label_fg,
            ),
        )

    def update_status_skipped(self, file_name):
        self.root.after(
            0,
            self.context.update_queue_display(fg=self.context.status_label_fg),
        )
        self.status_text = f"File skipped. Already exists: {file_name}"
        self.root.after(
            0,
            lambda: self.context.update_status(
                self.status_text,
                percent=0,
                fg=self.context.status_label_fg,
            ),
        )

    def download(self, url, download_type="video"):
        """
        Orchestrates the download process for a given URL using yt-dlp,
        with a fallback strategy for different formats.
        """
        self.percent_value = 0.0
        format_fallback_chain = self._get_format_fallback_chain(download_type)

        if self.context.success_frame:
            self.context.success_frame.destroy()

        self._update_initial_gui_status(download_type)
        self.context.safe_title = "Unknown Video"

        for i, (stream_format, merge_format) in enumerate(format_fallback_chain):
            is_last_attempt = i == len(format_fallback_chain) - 1
            self.context.pause_resume_disable(merge_format != "mkv" and download_type == "video")

            if i > 0:
                self.context.update_status(f"Retrying with format: {stream_format}...")

            try:
                cmd = self._build_ytdlp_command(url, stream_format, merge_format, download_type)
                return_code = self._execute_and_parse_ytdlp(cmd, download_type)

                if self.context.is_stopped or self.context.is_paused:
                    self._finalize_download(download_type)
                    return False  # Stop further processing if paused or stopped

                final_file_path = (
                    os.path.join(self.context.download_path, self.context.final_filename_check)
                    if self.context.final_filename_check
                    else None
                )
                file_exists = final_file_path and os.path.exists(final_file_path)

                if return_code == 0 or file_exists:
                    if file_exists and return_code != 0:
                        logger.warning(
                            f"yt-dlp exited with code {return_code} for {url}, "
                            f"but the file '{self.context.final_filename_check}' was found. Treating as success."
                        )
                    if (self.settings.get("audio_format") == "bestaudio" and 
                            self.settings.get("embed_thumbnail_in_audio") == "Yes" and 
                            not self.is_spotdl_download and not self.is_yt_download):
                        self._try_embed_thumbnail_if_supported()
                    break  # Success, exit fallback loop
                elif not is_last_attempt:
                    continue  # Try next format
                else:
                    raise Exception(f"Download failed with code {return_code} after all fallbacks.")

            except Exception as e:
                logger.error(f"Download attempt failed for {url}: {e}", exc_info=True)
                if is_last_attempt:
                    self.queue_manager.add_failed_url(url, download_type, str(e))
                    self.context.update_status(f"Download failed: {e}", error=True)
                    return False # Exit after final attempt fails
            finally:
                self.context.pause_resume_disable(False)

        self._finalize_download(download_type)
        return True

    def _get_format_fallback_chain(self, download_type):
        """Determines the format fallback chain based on settings."""
        if download_type == "audio":
            audio_format = self.settings.get("audio_format", "m4a")
            m4a_format = "bestaudio[ext=m4a]/bestaudio[ext=mp4]/bestaudio[acodec=aac]/bestaudio"

            if audio_format == "mp3":
                if self.is_ffmpeg_available:
                    return [("bestaudio", None)]  # For MP3 conversion
                else:
                    return [(m4a_format, None)]  # Fallback to M4A
            elif audio_format == "m4a":
                return [(m4a_format, None)]
            else:  # bestaudio etc.
                return [("bestaudio", None)]

        # Video format logic
        if not self.is_ffmpeg_available:
            return [("b", None)]
            
        format_setting = self.settings.get("stream_and_merge_format", "bestvideo+bestaudio/best-mkv")
        if format_setting == "b":
            return [("b", None)]
        if format_setting == "bestvideo+bestaudio/best-mp4":
            return [("bestvideo+bestaudio/best", "mp4"), ("b", None)]
        
        # Default to mkv with fallback
        return [("bestvideo+bestaudio/best", "mkv"), ("bestvideo+bestaudio/best", "mp4"), ("b", None)]

    def _build_ytdlp_command(self, url, stream_format, merge_format, download_type):
        """Builds the yt-dlp command list."""
        cmd = [self.context.ytdlp_path]
        
        if merge_format:
            cmd.extend(["--merge-output-format", merge_format])

        # Format selection
        if download_type == "audio":
            audio_format = self.settings.get("audio_format", "m4a")
            embed_thumb = self.settings.get("embed_thumbnail_in_audio") == "Yes" and self.is_ffmpeg_available

            cmd.extend(["--format", stream_format])
            if audio_format == "mp3" and self.is_ffmpeg_available:
                cmd.extend(["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"])
            
            if embed_thumb:
                if audio_format == "m4a" or (audio_format == "mp3" and self.is_ffmpeg_available):
                    cmd.extend(["--embed-thumbnail", "--no-write-thumbnail"])
                elif self.is_ffmpeg_available: # for 'bestaudio'
                    cmd.append("--write-thumbnail")
        else: # video
            cmd.extend(["--format", stream_format, "--no-write-thumbnail"])
            if self.is_ffmpeg_available:
                cmd.append("--embed-thumbnail")
        
        if not self.is_spotdl_download and self.is_ffmpeg_available:
            cmd.append("--embed-metadata")
        
        # Common options
        cmd.extend([
            "--no-overwrites", "--continue", "--output", "%(title)s-%(id)s.%(ext)s", url,
            "--limit-rate", self.settings.get("download_speed"),
            "--restrict-filenames", "--trim-filenames", "100",
            "--progress-template", "%(progress._percent_str)s",
            "--console-title", "--newline", "--yes-playlist", "--ignore-errors",
            "--no-abort-on-error", "--sleep-interval", "2", "--max-sleep-interval", "8",
            "--retries", "15", "--fragment-retries", "15", "--retry-sleep", "3",
            "--socket-timeout", "30", "--extractor-retries", "3",
            "--force-keyframes-at-cuts",
            "--paths", f"home:{self.context.download_path}",
            "--paths", f"temp:{self.context.download_path_temp}",
        ])

        if cookies_cmd := self.settings.get_cookies_cmd():
            cmd.extend(cookies_cmd)
        if self.settings.get("enable_download_archive"):
            cmd.extend(["--download-archive", self.settings.get("download_archive_path", "downloaded.txt")])
        if self.context.ffmpeg_status["is_ffmpeg_suite_downloaded"]:
            cmd.extend(["--ffmpeg-location", os.path.dirname(self.context.ffmpeg_path)])
            
        return [c for c in cmd if c]

    def _execute_and_parse_ytdlp(self, cmd, download_type):
        """Executes the yt-dlp command, parses its output, and updates the GUI."""
        while not self.context.check_internet_connection():
            if not self.custom_msg_box.custom_askyesno(
                self.root, "Waiting for Connection",
                "No internet connection detected!\nConnect to the internet to continue.\n\nClick 'Yes' to retry. Click 'No' to Exit",
                self.messagebox_font
            ):
                self.context.exit_app()
                return -1 # Indicate failure

        self._reset_per_download_context()

        process_kwargs = {
            "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "bufsize": 1,
            "universal_newlines": True, "encoding": "utf-8", "errors": "replace",
            "start_new_session": True,
        }
        if IS_WINDOWS:
            process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            process_kwargs["startupinfo"] = startupinfo

        process = subprocess.Popen(cmd, **process_kwargs)
        self.context.current_process = process

        output_lines = []
        for line in process.stdout:
            output_lines.append(line.strip())
            if self.context.is_stopped or self.context.is_paused or self.context.is_exit:
                break
            if process.poll() is not None:
                logger.warning("Download process terminated unexpectedly.")
                break
            self._parse_ytdlp_line(line, download_type)
        
        return_code = process.wait()

        if return_code != 0:
            final_file_path = (
                os.path.join(self.context.download_path, self.context.final_filename_check)
                if self.context.final_filename_check
                else None
            )
            file_exists = final_file_path and os.path.exists(final_file_path)

            if not file_exists:
                logger.error(f"yt-dlp command failed with exit code {return_code}")
                logger.error(f"Full command: {' '.join(cmd)}")
                logger.error("yt-dlp output:\n" + '\n'.join(output_lines))

        self.context.current_process = None
        return return_code

    def _reset_per_download_context(self):
        """Resets context variables specific to a single download attempt."""
        self.context.video_index = None
        self.context.total_videos = None
        self.context.is_playlist = False
        self.context.files_downloaded = 0
        self.context.final_filename_check = ""
        self.files_skipped_prev = 0
        self.files_skipped_current = 0

    def _parse_ytdlp_line(self, line, download_type):
        """Parses a single line of output from yt-dlp."""
        line = line.strip()
        if not line:
            return
            
        # Prioritize filename detection
        if line.startswith("DownloadedFile:"):
            self.context.final_filename_check = line.split("DownloadedFile:", 1)[1].strip()
            return
        
        audio_ext = "|m4a|mp3|opus|flac|wav|aac|ogg|wma"
        media_match = re.search(rf"(.*\.(?:mp4|mkv|webm|avi|mov|flv|m4v|wmv{audio_ext}))", line.strip().strip('"\''), re.IGNORECASE)
        if media_match:
            self.context.final_filename_check = os.path.basename(media_match.group(1))
            return
            
        # Progress detection
        if re.match(r"^\s*\d+\.\d+%\s*$", line):
            self._handle_progress_update(line, download_type)
            return
        
        # Playlist detection
        playlist_match = re.search(r"Downloading video (\d+) of (\d+)", line) or re.search(r"\[download\] Downloading video (\d+) of (\d+)", line)
        if playlist_match:
            self.context.video_index = int(playlist_match.group(1))
            self.context.total_videos = int(playlist_match.group(2))
            self.context.is_playlist = True
            return

        # Skipped file detection
        if any(indicator in line for indicator in ["has already been downloaded", "already present", "Skipping", "already in archive"]):
            self._handle_skipped_file(line, download_type)
            return

        # Title and status detection
        if "Destination:" in line:
            self.context.safe_title = os.path.basename(line.split("Destination:", 1)[1].strip())
        elif "Extracting URL:" in line:
            potential_title = line.split(":")[-1].strip()
            if potential_title and len(potential_title) < 100:
                self.context.safe_title = potential_title
        elif "[download] 100%" in line or "Deleting original file" in line:
             self.context.files_downloaded += 1
        
        self._update_status_from_line(line, download_type)

    def _handle_progress_update(self, line, download_type):
        """Handles a progress percentage update from yt-dlp."""
        try:
            percent_str = line.replace("%", "").strip()
            self.percent_value = float(percent_str)
            if self.context.is_resumed: self.context.is_resumed = False
            
            if self.percent_value > self.context.progress_bar.value:
                self.context.progress_bar.value = self.percent_value

            display_title = self.context.safe_title[:65] if self.context.safe_title else "Video"
            if self.context.is_playlist:
                status_text = f"↓ {download_type} {self.context.video_index}/{self.context.total_videos}: {display_title} - {self.percent_value}%"
            elif self.is_playlist_url and self.total_videos_in_playlist > 0:
                status_text = f"↓ {download_type} {self.video_index_in_playlist}/{self.total_videos_in_playlist}: {display_title} - {self.percent_value}%"
            else:
                status_text = f"↓ {display_title} - {self.percent_value}%"
            
            self.context.update_status(status_text, percent=self.percent_value)
        except (ValueError, AttributeError):
            pass # Ignore parsing or GUI errors

    def _handle_skipped_file(self, line, download_type):
        """Handles a skipped file message from yt-dlp."""
        self.files_skipped_current += 1
        if expected_filename := self.extract_filename_from_skip_line(line):
            base_name = os.path.basename(expected_filename)
            self.cleanup_associated_thumbnails(os.path.join(self.context.download_path, base_name))
            self.cleanup_associated_thumbnails(os.path.join(self.context.download_path_temp, base_name))

        display_title = self.context.safe_title[:65] if self.context.safe_title else "File"
        if self.context.is_playlist:
            status_text = f"↷ {download_type} {self.context.video_index}/{self.context.total_videos}: Skipped - {display_title}"
        elif self.is_playlist_url and self.total_videos_in_playlist > 0:
            status_text = f"↷ {download_type} {self.video_index_in_playlist}/{self.total_videos_in_playlist}: Skipped - {display_title}"
        else:
            status_text = f"↷ Skipped: {display_title} (already downloaded)"
        
        self.context.update_status(status_text, percent=0)
        
        if self.context.safe_title:
            base_name = self.get_base_name_from_ytdlp_file(self.context.safe_title)
            self.cleanup_video_leftovers(base_name, self.context.download_path_temp)

    def _update_status_from_line(self, line, download_type):
        """Updates the status label based on various yt-dlp output lines."""
        if not self.context.safe_title or self.context.safe_title == "Unknown Video":
            return
            
        display_title = self.context.safe_title[:65]
        status_text = ""

        if self.context.is_resumed:
            status_text = f"{self.style_manager.get_emoji('loading')} Resuming: {display_title}"
        elif "[extractaudio]" in line or "[embedthumbnail]" in line or "[movefiles]" in line:
            status_text = f"{self.style_manager.get_emoji('loading')} Processing: {display_title}"
        elif self.context.is_playlist:
            status_text = f"{self.style_manager.get_emoji('loading')} {download_type} {self.context.video_index}/{self.context.total_videos}: {display_title}"
        elif self.is_playlist_url and self.total_videos_in_playlist > 0:
            status_text = f"{self.style_manager.get_emoji('loading')} {download_type} {self.video_index_in_playlist}/{self.total_videos_in_playlist}: {display_title}"
        else:
            status_text = f"{self.style_manager.get_emoji('loading')} Preparing: {display_title}"
        
        if status_text:
            self.context.update_status(status_text, percent=0)

    def _finalize_download(self, download_type):
        """Handles final actions after a download attempt (success or failure)."""
        if self.context.is_stopped or self.context.is_paused:
            status = "paused" if self.context.is_paused else "stopped"
            emoji = self.style_manager.get_emoji('pause' if self.context.is_paused else 'stop')
            self.context.update_status(f"{emoji} Download {status}: {self.context.recent_url}", percent=self.context.progress_bar.value)
            self.context.current_download_url = None
            self.context.paused_url = None
            if self.context.is_stopped:
                self.context.is_stopped = False # Reset flag
            return

        if self.files_skipped_current > self.files_skipped_prev:
            self.status_text = "Skipped. Check if already downloaded"
            if not self.is_spotdl_download:
                self.queue_manager.remove_url()
            self.files_skipped_prev = self.files_skipped_current
        elif not self.is_spotdl_download and not self.is_yt_download:
             self.status_text = "✓ Download complete"
             self.queue_manager.remove_url()

        if self.context.final_filename_check and self.check_files_exist_by_base(self.context.final_filename_check.rsplit('.', 1)[0], self.context.download_path):
             base_name = self.get_base_name_from_ytdlp_file(self.context.final_filename_check)
             self.context.add_to_delete_list(base_name, self.context.download_path_temp)

        self.context.update_status(self.status_text, percent=0)
        self.rename_fully_downloaded_part_files(self.context.download_path)
        self.rename_fully_downloaded_part_files(self.context.download_path_temp)
        self.context.safe_title = ""

    def extract_filename_from_skip_line(self, line):
        """Extract filename from yt-dlp's skip messages"""
        # Pattern 1: "[download] filename.ext has already been downloaded"
        match = re.search(r"\[download\]\s+([^\s]+\.\w+)\s+has already", line)
        if match:
            return match.group(1)

        # Pattern 2: "File 'filename.ext' is already present"
        match = re.search(r"File\s+'([^']+)'\s+is already present", line)
        if match:
            return match.group(1)

        # Pattern 3: "Skipping filename.ext"
        match = re.search(r"Skipping\s+([^\s]+\.\w+)", line)
        if match:
            return match.group(1)

        return None

    def _try_embed_thumbnail_if_supported(self):
        """Try to embed thumbnail after download if format supports it"""
        if not self.context.final_filename_check:
            return

        if not self.is_ffmpeg_available:
            print("ffmpeg not available for thumbnail embedding")
            return

        audio_file = os.path.join(self.context.download_path, self.context.final_filename_check)
        thumbnail_file = self._find_thumbnail_file(audio_file)

        if not (
            thumbnail_file
            and os.path.exists(thumbnail_file)
            and os.path.exists(audio_file)
        ):
            return

        # Step 1: Convert thumbnail to PNG first
        png_thumbnail = thumbnail_file.rsplit(".", 1)[0] + ".png"

        if not self.png_thumbnail_exists(thumbnail_file.rsplit(".", 1)[0]):
            convert_cmd = [
                self.ffmpeg,
                "-i",
                thumbnail_file,
                "-frames:v",
                "1",  # Handle animated WebP/GIF
                png_thumbnail,
            ]
            process_kwargs = {
                "capture_output": True,
                "check": True
            }

            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                
            subprocess.run(convert_cmd, **process_kwargs)

        embed_cmd = ""
        try:
            # Use ffmpeg to embed thumbnail
            if audio_file.lower().endswith(
                (".mp3", ".m4a", ".mp4", ".aac", ".flac", ".mkv", ".mka")
            ):
                audio_file_temp = (
                    audio_file.rsplit(".", 1)[0]
                    + "_temp."
                    + audio_file.rsplit(".", 1)[1]
                )
                embed_cmd = [
                    self.ffmpeg,
                    "-i",
                    audio_file,
                    "-i",
                    png_thumbnail,
                    "-c",
                    "copy",
                    "-map",
                    "0",
                    "-map",
                    "1",
                    "-disposition:v",
                    "attached_pic",
                    audio_file_temp,
                ]
            subprocess.run(embed_cmd, capture_output=True, text=True, check=True)
            os.replace(audio_file_temp, audio_file)
            self.delete_thumbnail_images(thumbnail_file)
            print("✓ Thumbnail embedded successfully")
        except Exception as e:
            print(f"Thumbnail embedding failed, keeping separate file: {e}")

    def add_thumbnail_to_opus(self, opus_file: Path, cover_file_orig: Path) -> bool:
        """Add/replace cover art in an Opus file using base64 encoding."""
        try:
            opus_file = Path(opus_file) if isinstance(opus_file, str) else opus_file
            cover_file = Path(cover_file_orig) if isinstance(cover_file_orig, str) else cover_file_orig

            # Convert WebP to JPEG if needed
            if cover_file.suffix.lower() == '.webp':
                temp_jpg = tempfile.mktemp(suffix='.jpg')
                
                with Image.open(cover_file) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(temp_jpg, 'JPEG', quality=90)
                    cover_file = Path(temp_jpg)
            
            # Read image data
            with open(cover_file, 'rb') as f:
                image_data = f.read()
            
            # Create FLAC Picture block
            picture = Picture()
            picture.type = PictureType.COVER_FRONT
            picture.mime = 'image/jpeg'  # Always use JPEG for compatibility
            picture.desc = 'Cover'
            picture.data = image_data
            
            # Encode to base64 string (THIS IS WHAT MUTAGEN EXPECTS!)
            encoded_picture = base64.b64encode(picture.write()).decode('ascii')
            
            # Load Opus and save metadata
            audio = OggOpus(str(opus_file))
            audio['metadata_block_picture'] = encoded_picture

            audio.save()
            
            # print(f"✅ Cover embedded in Opus")
            
            webm_file = opus_file.with_suffix(".webm")
            if webm_file and os.path.exists(webm_file):
                os.remove(webm_file)
            if cover_file_orig:
                # os.remove(cover_file_orig)
                self.delete_thumbnail_images(cover_file_orig)
            
            return True
            
        except ImportError as e:
            print(f"❌ Missing dependency: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed: {type(e).__name__}: {e}")
            return False
        
    def png_thumbnail_exists(self, base_name):
        possible_names = [
            base_name + ".png",
            base_name + ".PNG",
            base_name + ".Png",
            # Add other case variations if needed
        ]
        return any(os.path.exists(name) for name in possible_names)

    def _find_thumbnail_file(self, audio_file):
        """Find thumbnail file with any common image extension"""
        base_name = audio_file.rsplit(".", 1)[0]
        image_extensions = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]

        for ext in image_extensions:
            thumbnail_file = base_name + ext
            if os.path.exists(thumbnail_file):
                return thumbnail_file

        return None

    def delete_thumbnail_images(self, thumbnail_file):
        """Delete thumbnail file and any common image format variants"""
        # import os

        if not thumbnail_file or not os.path.exists(thumbnail_file):
            print(f"File not found: {thumbnail_file}")
            return

        # Get base name without extension
        base_name = thumbnail_file.rsplit(".", 1)[0]

        # Common image extensions to check
        image_extensions = [
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
            ".gif",
            ".tiff",
            ".tif",
            ".ico",
            ".svg",
        ]

        # Delete the original file
        try:
            os.remove(thumbnail_file)
        except OSError as e:
            print(f"❌ Could not delete {thumbnail_file}: {e}")

        # Delete any other image format variants
        for ext in image_extensions:
            other_thumbnail_file = base_name + ext
            if os.path.exists(other_thumbnail_file):
                try:
                    os.remove(other_thumbnail_file)
                except OSError as e:
                    print(f"❌ Could not delete {other_thumbnail_file}: {e}")

    def check_files_exist_by_base(self, base_name, folder_path):
        """Check if any files exist with this base name"""
        # print(os.path.join(folder_path, f"{base_name}"))
        pattern = os.path.join(folder_path, f"{base_name}.*")
        matching_files = glob.glob(pattern)
        return len(matching_files) > 0, matching_files

    def cleanup_video_leftovers(self, base_name, download_path):
        """Clean up incomplete files for a specific video that was skipped or failed"""

        # Find all files that start with this base name
        all_related_files = glob.glob(os.path.join(download_path, f"{base_name}*"))
        # Check if this download has incomplete indicators
        has_incomplete_indicators = False
        incomplete_patterns = [
            f"{base_name}.temp.mkv",
            f"{base_name}.temp.mp4",
            f"{base_name}.f*.mp4",
            f"{base_name}.f*.webm",
            f"{base_name}.part",
            f"{base_name}*.part",
            f"{base_name}*.webp",
            f"{base_name}*.ytdl",
        ]

        # Check if any incomplete files exist
        for pattern in incomplete_patterns:
            if glob.glob(os.path.join(download_path, pattern)):
                has_incomplete_indicators = True
                break

        if not has_incomplete_indicators:
            return

        # Files to delete (only definitive temporary files)
        files_to_delete = []
        for file_path in all_related_files:
            file_name = os.path.basename(file_path)

            # Delete only these specific temporary file types
            if (
                file_name.endswith((".temp.mkv", ".temp.mp4", ".part", ".ytdl"))
                or re.search(r"\.f\d+\..+", file_name)  # Fragment files like .f401.mp4
                or file_name
                in [f"{base_name}.webp", f"{base_name}.jpg", f"{base_name}.png"]
            ):

                files_to_delete.append(file_path)

        # Delete the files
        cleaned_count = 0
        for file_to_delete in files_to_delete:
            try:
                os.remove(file_to_delete)
                # print(f"  Deleted incomplete file: {os.path.basename(file_to_delete)}")
                cleaned_count += 1
            except OSError as e:
                # print(f"  Failed to delete {file_to_delete}: {e}")
                pass

        # print(f"Cleaned up {cleaned_count} incomplete files for: {base_name}")

    def rename_fully_downloaded_part_files(self, download_path):
        """Cross-platform cleanup with better error handling"""

        try:
            # Normalize and validate paths
            download_path = os.path.abspath(os.path.normpath(download_path))
            main_download_path = os.path.abspath(os.path.normpath(self.context.download_path))

            # Ensure directories exist
            os.makedirs(main_download_path, exist_ok=True)

            pattern = os.path.join(download_path, "*.part")

            for part_file in glob.glob(pattern):
                try:
                    if self.is_video_complete(part_file):
                        self._process_completed_part_file(
                            part_file, download_path, main_download_path
                        )
                except Exception as e:
                    print(f"Error processing {part_file}: {e}")
                    continue

        except Exception as e:
            print(f"Error in cleanup process: {e}")

    def _process_completed_part_file(self, part_file, source_path, dest_path):
        """Process a single completed part file"""
        filename = os.path.basename(part_file).replace(".part", "")
        final_video_path = os.path.join(dest_path, filename)

        # Check if destination already exists
        if os.path.exists(final_video_path):
            print(f"Destination exists, removing source: {filename}")
            os.remove(part_file)
            return

        # Cleanup thumbnails
        self.cleanup_associated_thumbnails(os.path.splitext(part_file)[0])

    def cleanup_associated_thumbnails(self, base_name):
        """Remove thumbnail files associated with the video"""
        # Common thumbnail extensions that yt-dlp might create
        thumbnail_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        base_name = os.path.splitext(base_name)[0]
        for ext in thumbnail_extensions:
            thumb_path = base_name + ext
            if os.path.exists(thumb_path):
                try:
                    os.remove(thumb_path)
                    # print(f"Removed leftover thumbnail: {thumb_path}")
                except OSError as e:
                    print(f"Failed to remove thumbnail {thumb_path}: {e}")

    def is_video_complete(self, file_path):
        """Check if video file is complete - cross-platform"""
        try:
            # Use your existing ffprobe path detection
            ffprobe_cmd = [
                self.ffprobe,  # This should already be cross-platform
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                file_path,
            ]

            process_kwargs = {}
            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

                # Optional: Additional window hiding for extra reliability
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                process_kwargs["startupinfo"] = startupinfo

            result = subprocess.run(
                ffprobe_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                **process_kwargs,  # Your cross-platform subprocess settings
            )

            # Check if we got a valid duration
            return (
                result.returncode == 0
                and result.stdout.strip()
                and float(result.stdout.strip()) > 0
            )

        except (subprocess.TimeoutExpired, ValueError, OSError):
            return False

    def pause_download(self, process=None):
        """Pause the current download process"""

        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process
        if (
            process
            and self.context.is_downloading
            and not self.context.is_paused
            and not self.context.is_stopped
        ) or (
            self.is_spotdl_download
            and not self.context.is_paused
            and not self.context.is_stopped
        ):
            try:
                self.stop_download("pause", process)

            except Exception as e:
                print(f"Error pausing download: {e}")
                self.custom_msg_box.custom_showerror(
                    self.root,
                    "Error",
                    f"Failed to pause download: {str(e)}",
                    self.messagebox_font,
                )
        elif not self.context.is_downloading:
            # messagebox.showinfo("Info", "No download in progress to pause")
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No download in progress to pause",
                self.messagebox_font,
            )
        elif self.context.is_paused:
            # messagebox.showinfo("Info", "Download is already paused")
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "Download is already paused",
                self.messagebox_font,
            )
        elif self.context.is_stopped:
            # messagebox.showinfo("Info", "Download is already stopped")
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "Download is already stopped",
                self.messagebox_font,
            )

        elif (
            not process
            or process.poll() is not None
        ):
            # messagebox.showinfo("Info", "No active download process to pause")
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No active download process to pause",
                self.messagebox_font,
            )

    def resume_download(self, process=None):
        """Resume the current download process"""
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        if self.context.is_paused and not self.context.is_stopped:
            try:
                if self.queue_manager.get_queue_count() == 0:
                    self.context.update_status(
                        f"Empty Queue.txt No URLs to download",
                        percent=self.context.progress_bar.value,
                        fg=self.context.status_label_fg,
                    )
                else:
                    self.context.is_resumed = True
                    self.context.is_paused = False

                    self.context.update_status(
                        f"{self.style_manager.get_emoji('play')} Resuming download... {self.context.recent_url} {self.context.progress_bar.value}%",
                        percent=self.context.progress_bar.value,
                        fg=self.context.status_label_fg,
                    )

                    if not self.context.is_downloading: # Start queue processing if not already running
                        self.context.start_queue_processing()

            except Exception as e:
                print(f"Error resuming download: {e}")
                self.custom_msg_box.custom_showerror(
                    self.root,
                    "Error",
                    f"Failed to resume download: {str(e)}",
                    self.messagebox_font,
                )

        elif not self.context.is_paused:
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No paused download to resume",
                self.messagebox_font,
            )

        elif self.context.is_stopped:
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "Download was stopped and cannot be resumed",
                self.messagebox_font,
            )

        elif (
            not process
            or process.poll() is not None
        ):
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No active download process to resume",
                self.messagebox_font,
            )

    def stop_download(self, stop_condition="stop", process=None):
        """Stop the current download process, pause_download() also calls this"""
        if self.is_spotdl_download:
            self.context.cancel_spotdl_event.set()
            time.sleep(1)
        
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        if not self._should_stop_download(process) and not self.is_spotdl_download:
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No active download process to pause/stop",
                self.messagebox_font,
            )
            return

        current_url = self.context.current_download_url
        if self.context.download_type == "audio" and current_url:
            current_url = "audio:" + current_url

        if self.context.is_paused and stop_condition == "stop":
            self.context.is_after_stopped = True
            self.context.is_paused = False
            self.queue_manager.remove_url(current_url)
            self.context.update_status(
                f"{self.style_manager.get_emoji('stop')} Download stopped: {self.context.recent_url} {self.context.progress_bar.value}% ",
                percent=0,
                fg=self.context.status_label_fg,
            )
            if hasattr(self.context, "safe_title") and self.context.safe_title:
                # base_name = self.context.safe_title.split(".")[0].strip()
                base_name = self.get_base_name_from_ytdlp_file(self.context.safe_title)
                self.cleanup_video_leftovers(base_name, self.context.download_path_temp)
                self.cleanup_video_leftovers(base_name, self.context.download_path)
                self.context.add_to_delete_list(
                    base_name, self.context.download_path_temp
                )
            self.context.start_queue_processing()
            return

        if stop_condition == "pause":
            self.context.is_stopped = False
            self.context.is_paused = True
            self.context.is_resumed = False
            self.context.paused_url = current_url
        else:
            self.context.is_stopped = True
            self.context.is_paused = False
            # Get current URL and remove from queue
            current_url = self.queue_manager.remove_url(current_url)

        # Stop the download process if active
        if process and self.context.is_downloading:
            try:
                self.stop_download_core(process)
            except:
                pass

        # Clear process reference and state
        self._reset_download_state(process)

        if stop_condition == "pause":
            self.context.update_status(
                f"{self.style_manager.get_emoji('stop')} Download paused: {self.context.recent_url} {self.context.progress_bar.value}%",
                percent=self.context.progress_bar.value,
                fg=self.context.status_label_fg,
            )
            # print("Download pause completed")
        else:
            self.context.update_status(
                f"{self.style_manager.get_emoji('stop')} Download stopped: {self.context.recent_url} {self.context.progress_bar.value}%",
                percent=0,
                fg=self.context.status_label_fg,
            )
            # print("Download stop completed")

        if stop_condition == "stop":
            # self.context.is_after_stopped = True
            if hasattr(self.context, "safe_title") and self.context.safe_title:
                # base_name = self.context.safe_title.split(".")[0].strip()
                base_name = self.get_base_name_from_ytdlp_file(self.context.safe_title)
                self.cleanup_video_leftovers(base_name, self.context.download_path_temp)
                self.context.add_to_delete_list(
                    base_name, self.context.download_path_temp
                )

            self.context.start_queue_processing()

    def _should_stop_download(self, process=None):
        """Check if download should be stopped"""
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        return (
            self.context.is_paused
            and not process
            and not self.context.is_downloading
        ) or (process and self.context.is_downloading)

    def _reset_download_state(self, process=None):
        """Reset all download state variables"""
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        process = None
        self.context.is_downloading = False
        self.context.current_download_url = None

    def _check_psutil_availability(self):
        """Check if psutil is available without raising ImportError"""
        try:
            # import psutil

            return True
        except ImportError:
            return False

    def stop_download_core(self, process=None):
        """Stop the current download process with cross-platform process tree termination"""
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        self.terminate_process_minimal_version(process)
        time.sleep(0.5)  # Give some time to ensure process is terminated
        if not process:
            return
        
        for attempt in range(MAX_TERMINATION_ATTEMPTS):
            try:
                logger.info(f"Attempt {attempt + 1} to terminate download process")

                if IS_WINDOWS:
                    success = self._terminate_windows(process)
                else:
                    success = self._terminate_unix(process)

                if success:
                    logger.info("Download process terminated successfully")
                    break

            except Exception as e:
                logger.error(f"Termination attempt {attempt + 1} failed: {e}")
                if attempt == MAX_TERMINATION_ATTEMPTS - 1:
                    self._handle_termination_failure(e)

        self._cleanup_after_termination()

    def _terminate_windows(self, process=None):
        """Windows-specific process termination"""
        logger.info("Terminating process tree on Windows...")
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        # Method 1: Try Windows API first (most reliable)
        if self._terminate_with_windows_api(process):
            return True

        # Method 2: Try taskkill
        if self._terminate_with_taskkill(process):
            return True

        # Method 3: Fallback to psutil
        if self._check_psutil_availability():
            if self._terminate_with_psutil(process):
                return True

        # Method 4: Final basic fallback
        return self._terminate_basic(process)

    def _terminate_with_windows_api(self, process=None):
        """Use Windows API for process termination"""
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        try:
            # import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(
                0x0001, False, process.pid
            )  # PROCESS_TERMINATE
            if handle:
                result = kernel32.TerminateProcess(handle, 0)
                kernel32.CloseHandle(handle)
                if result:
                    logger.info("Process terminated using Windows API")
                    return True
        except Exception as e:
            logger.debug(f"Windows API termination failed: {e}")
        return False

    def _terminate_with_taskkill(self, process=None):
        """Use taskkill for process termination on Windows"""
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        try:
            result = subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(process.pid),
                    "/T",  # Terminate child processes
                    "/F",  # Force termination
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_GRACEFUL,
            )

            if result.returncode == 0:
                logger.info("Process tree terminated successfully with taskkill")
                return True
            else:
                logger.warning(f"taskkill failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.warning("taskkill timed out")
        except FileNotFoundError:
            logger.warning("taskkill not available")
        except Exception as e:
            logger.debug(f"taskkill error: {e}")

        return False

    def _terminate_unix(self, process=None):
        """Unix-like systems (Linux/Mac) process termination"""
        logger.info("Terminating process tree on Unix/Linux/Mac...")
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        # Method 1: Process group termination
        if self._terminate_process_group(process):
            return True

        # Method 2: psutil fallback
        if self._terminate_with_psutil(process):
            return True

        # Method 3: Basic fallback
        return self._terminate_basic(process)

    def _terminate_process_group(self, process=None):
        """Terminate entire process group on Unix systems"""
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        try:
            # import signal

            # Get process group ID
            pgid = os.getpgid(process.pid)
            logger.info(f"Terminating process group {pgid}")

            # Send SIGTERM to entire process group
            os.killpg(pgid, signal.SIGTERM)

            # Wait for graceful termination
            try:
                process.wait(timeout=TIMEOUT_GRACEFUL)
                logger.info("Process group terminated with SIGTERM")
                return True
            except subprocess.TimeoutExpired:
                logger.warning("SIGTERM timeout, sending SIGKILL to process group")
                # Force kill entire process group
                os.killpg(pgid, signal.SIGKILL)
                try:
                    process.wait(timeout=TIMEOUT_FORCE)
                    logger.info("Process group killed with SIGKILL")
                    return True
                except subprocess.TimeoutExpired:
                    logger.error("Process group still running after SIGKILL")

        except (OSError, AttributeError, ProcessLookupError) as e:
            logger.warning(f"Process group termination failed: {e}")

        return False

    def _terminate_with_psutil(self, process=None):
        """Fallback method using psutil for process termination"""
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        try:
            # import psutil

            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)

            # Terminate children first
            for child in children:
                try:
                    child.terminate()
                    logger.debug(f"Terminated child process: {child.pid}")
                except psutil.NoSuchProcess:
                    logger.debug(f"Child process already terminated: {child.pid}")
                except Exception as e:
                    logger.warning(f"Failed to terminate child {child.pid}: {e}")

            # Then terminate parent
            try:
                parent.terminate()
            except psutil.NoSuchProcess:
                logger.debug("Parent process already terminated")
                return True

            # Wait for all processes to terminate
            gone, alive = psutil.wait_procs(
                [parent] + children, timeout=TIMEOUT_GRACEFUL
            )

            # Force kill any remaining processes
            for process in alive:
                try:
                    process.kill()
                    logger.debug(f"Force killed process: {process.pid}")
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    logger.warning(f"Failed to kill process {process.pid}: {e}")

            # Verify all processes are gone
            gone, alive = psutil.wait_procs(alive, timeout=TIMEOUT_FORCE)
            if not alive:
                logger.info("Process terminated using psutil")
                return True
            else:
                logger.warning(
                    f"{len(alive)} processes still alive after psutil termination"
                )

        except ImportError:
            logger.warning("psutil not available")
        except Exception as e:
            logger.error(f"psutil termination failed: {e}")

        return False

    def _terminate_basic(self, process=None):
        """Basic fallback termination method"""
        if process is None and self.context.current_process:
            process = self.context.current_process
        elif process is None and self.context.stopdl_process:
            process = self.context.stopdl_process

        try:
            # Try graceful termination first
            process.terminate()
            try:
                process.wait(timeout=TIMEOUT_GRACEFUL)
                logger.info("Process terminated (basic fallback)")
                return True
            except subprocess.TimeoutExpired:
                # Force kill if graceful fails
                process.kill()
                try:
                    process.wait(timeout=TIMEOUT_FORCE)
                    logger.info("Process killed (basic fallback)")
                    return True
                except subprocess.TimeoutExpired:
                    logger.error("Process still running after basic termination")

        except Exception as e:
            logger.error(f"Basic termination failed: {e}")

        return False

    def _handle_termination_failure(self, error):
        """Handle complete termination failure"""
        error_msg = f"Failed to stop download after {MAX_TERMINATION_ATTEMPTS} attempts: {str(error)}"
        logger.error(error_msg)
        # messagebox.showerror("Error", error_msg)
        self.custom_msg_box.custom_showerror(
            self.root,
            "Error",
            error_msg,
            self.messagebox_font,
        )

        # Set flag for manual cleanup needed
        self.requires_manual_cleanup = True

    def _cleanup_after_termination(self):
        """Cleanup after termination attempt"""
        try:
            # Reset stop flag after a short delay to allow cleanup
            self.root.after(100, lambda: setattr(self, "is_stopped", False))
            # Update queue display immediately
            self.root.after(
                0,
                self.context.update_queue_display(fg=self.context.status_label_fg),
            )

            # Additional cleanup if needed
            if (
                hasattr(self, "requires_manual_cleanup")
                and self.requires_manual_cleanup
            ):
                logger.warning("Manual cleanup may be required for orphaned processes")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def get_base_name_from_ytdlp_file(self, filename):
        """
        Extract base filename from yt-dlp download files, handling all temporary formats.

        Args:
            filename: Full filename or path

        Returns:
            Base name without format codes, extensions, or temp suffixes

        Examples:
            "video.f401.mp4" -> "video"
            "video.f251-9.webm.part" -> "video"
            "video.temp.mkv" -> "video"
            "video.webp" -> "video"
        """
        # Get just the filename without directory path
        filename = os.path.basename(filename)

        # Remove common extensions iteratively (handles .mp4.part, etc)
        extensions_to_strip = [
            ".part",
            ".ytdl",
            ".temp.mkv",
            ".temp.mp4",
            ".temp.webm",
            ".mkv",
            ".mp4",
            ".webm",
            ".webp",
            ".jpg",
            ".jpeg",
            ".png",
        ]

        # Keep stripping until no more matches
        changed = True
        while changed:
            changed = False
            for ext in extensions_to_strip:
                if filename.lower().endswith(ext):
                    filename = filename[: -len(ext)]
                    changed = True
                    break

        # Remove yt-dlp format codes (e.g., .f401, .f251-9)
        # Pattern matches: .f followed by digits, optionally followed by -digits
        filename = re.sub(r"\.[f]\d+(-\d+)?$", "", filename, flags=re.IGNORECASE)

        return filename

    def _get_complete_artist_discography(self, artist_id):
        """
        Get complete list of unique tracks from all artist releases.
        Deduplicates tracks that appear in multiple albums/releases.
        """
        releases = self._get_all_artist_releases(artist_id)
        
        if not releases:
            return []
        
        all_tracks = []
        track_ids = set()
        
        for i, release in enumerate(releases, 1):
            try:
                release_tracks = self._get_tracks_from_release(release['id'])
                
                for track in release_tracks:
                    if track and 'id' in track and track['id']:
                        if track['id'] not in track_ids:
                            track_ids.add(track['id'])
                            all_tracks.append(track)
                
                if i % 10 == 0 or i == len(releases):
                    print(f"   Processed {i}/{len(releases)} releases... Found {len(all_tracks)} unique tracks")
                    
            except Exception as e:
                print(f"   ⚠️ Error processing release: {e}")
                continue
        
        print(f"\n✅ Total unique tracks found: {len(all_tracks)}")
        return all_tracks


    def _get_all_artist_releases(self, artist_id):
        """
        Get ALL releases for an artist (albums, singles, compilations).
        Handles pagination and deduplication.
        """
        all_releases = []
        album_groups = ['album', 'single', 'compilation']
        
        print("🔍 Fetching artist's releases...")
        
        for group in album_groups:
            print(f"   Scanning '{group}'...")
            releases = []
            results = self.sp.artist_albums(
                artist_id,
                album_type=None,
                country=None,
                limit=50,
                offset=0
            )
            
            group_releases = [item for item in results['items'] if item['album_group'] == group]
            releases.extend(group_releases)
            
            while results['next']:
                results = self.sp.next(results)
                group_releases = [item for item in results['items'] if item['album_group'] == group]
                releases.extend(group_releases)
            
            print(f"     Found {len(releases)} releases in '{group}'")
            all_releases.extend(releases)
        
        unique_releases = {}
        for release in all_releases:
            unique_releases[release['id']] = release
        
        print(f"✅ Total unique releases: {len(unique_releases)}")
        return list(unique_releases.values())


    def _get_tracks_from_release(self, release_id):
        """
        Get all tracks from a specific release.
        Handles pagination for releases with many tracks.
        """
        tracks = []
        results = self.sp.album_tracks(release_id, limit=50)
        tracks.extend(results['items'])
        
        while results['next']:
            results = self.sp.next(results)
            tracks.extend(results['items'])
        
        return tracks

    def save_to_file(self, all_tracks, artist_name, artist_id):
        """Save all track URLs to a file."""
        # Create filename
        safe_name = "".join(c for c in artist_name if c.isalnum() or c in (' ', '-')).rstrip()
        filename = f"spotify_{safe_name}_{artist_id}_FULL_DISCOGRAPHY.txt"
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# Complete Spotify Discography for {artist_name}\n")
            f.write(f"# Artist ID: {artist_id}\n")
            f.write(f"# Total Tracks: {len(all_tracks)}\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("#" * 60 + "\n\n")
            
            # Group by release type
            releases_by_type = {}
            for track in all_tracks:
                release_type = track.get('release_type', 'unknown')
                if release_type not in releases_by_type:
                    releases_by_type[release_type] = []
                releases_by_type[release_type].append(track)
            
            # Write tracks grouped by type
            for release_type in sorted(releases_by_type.keys()):
                f.write(f"\n# ===== {release_type.upper()} =====\n")
                for track in releases_by_type[release_type]:
                    if 'external_urls' in track and 'spotify' in track['external_urls']:
                        f.write(f"{track['external_urls']['spotify']}\n")
        
        print(f"💾 Full discography saved to: {filename}")
        return filename

    def process_spotify_url(self, url):
        """
        Extract metadata and type from any Spotify URL.
        Returns: (collection_id, collection_type, is_single_track)
        """
        url = url.strip()
        is_single_track = False
        
        # Handle Spotify URI format
        if url.startswith('spotify:'):
            parts = url.split(':')
            if len(parts) >= 3:
                collection_type = parts[1]  # track, album, artist, playlist
                collection_id = parts[2]
                if collection_type == 'track':
                    is_single_track = True
                return collection_id, collection_type, is_single_track
        
        # Handle web URL format
        if "open.spotify.com" in url:
            # Remove query parameters
            clean_url = url.split('?')[0]
            
            # Check for single track
            if "/track/" in clean_url:
                collection_id = clean_url.split("/track/")[-1]
                return collection_id, "track", True
            
            # Check for other collection types
            elif "/artist/" in clean_url:
                collection_id = clean_url.split("/artist/")[-1]
                return collection_id, "artist", False
                
            elif "/album/" in clean_url:
                collection_id = clean_url.split("/album/")[-1]
                return collection_id, "album", False
                
            elif "/playlist/" in clean_url:
                collection_id = clean_url.split("/playlist/")[-1]
                return collection_id, "playlist", False
                
            elif "/show/" in clean_url:  # Podcast
                collection_id = clean_url.split("/show/")[-1]
                return collection_id, "show", False
                
            elif "/episode/" in clean_url:  # Podcast episode
                collection_id = clean_url.split("/episode/")[-1]
                return collection_id, "episode", False
        
        # If it's just an ID, try to determine type from length/pattern
        # Spotify IDs are typically 22 characters
        if len(url) == 22 and url.isalnum():
            # This is ambiguous - could be any type
            # You might want to prompt user or try multiple endpoints
            return url, "unknown", False
        
        raise ValueError(f"Could not parse Spotify URL: {url}")

    def get_urls_and_metadata(self, collection_id, collection_type):
        """
        Fetch MINIMAL essential metadata for any Spotify collection.
        Handles: album, playlist, artist, track
        Returns only what's needed for downloading and organizing.
        """
        try:
            result = {
                'collection_type': collection_type,
                'collection_id': collection_id,
                'collection_name': '',
                'collection_artist': '',
                'tracks': [],
                'total_tracks': 0
            }

            if collection_type == 'album':
                album_info = self.sp.album(collection_id)
                result['collection_name'] = album_info['name']
                try:
                    result['collection_artist'] = album_info['artists'][0]['name']
                except:
                    print("Could not find artist name")

                result['total_tracks'] = album_info['total_tracks']
                
                # Process tracks with their original album track numbers
                for idx, track_data in enumerate(album_info['tracks']['items'], 1):
                    track_info = self._extract_track_metadata(track_data, track_number=idx)
                    result['tracks'].append(track_info)

                print(result['total_tracks'])

            elif collection_type == 'playlist':
                playlist_info = self.sp.playlist(collection_id)
                result['collection_name'] = playlist_info['name']
                result['total_tracks'] = playlist_info['tracks']['total']
                
                # Use enumerated index as track_number for playlists (since they're inconsistent)
                for idx, item in enumerate(playlist_info['tracks']['items'], 1):
                    track_data = item['track']
                    if track_data:  # Skip null tracks
                        track_info = self._extract_track_metadata(track_data, track_number=idx)
                        result['tracks'].append(track_info)

                print(result['total_tracks'])

            elif collection_type == 'artist':
                artist_info = self.sp.artist(collection_id)
                result['collection_name'] = artist_info['name']
                all_tracks = self._get_complete_artist_discography(collection_id)
                result['total_tracks'] = len(all_tracks)
                print(result['total_tracks'])
                for idx, track_data in enumerate(all_tracks, 1):
                    track_info = self._extract_track_metadata(track_data, track_number=idx)
                    result['tracks'].append(track_info)

            elif collection_type == 'track':
                track_data = self.sp.track(collection_id)
                result['collection_name'] = track_data['name']
                result['total_tracks'] = 1
                
                # Single track gets track_number 1
                track_info = self._extract_track_metadata(track_data, track_number=1)
                result['tracks'].append(track_info)

            else:
                raise ValueError(f"Unsupported collection_type: {collection_type}")

            return result

        except Exception as e:
            print(f"Error fetching metadata for {collection_type} {collection_id}: {e}")
            return None
    def _extract_track_metadata(self, track_data, track_number):
        """
        Extract minimal metadata from a track object.
        Works for all collection types.
        
        Args:
            track_data: The track object from Spotify API
            track_number: Sequential number (1, 2, 3...) for organizing
        
        Returns:
            dict with track metadata
        """
        # Handle null tracks (can happen in playlists)
        if not track_data or track_data is None:
            return None

        # Extract basic info
        track_name = track_data.get('name', 'Unknown')
        track_id = track_data.get('id', '')
        duration_ms = track_data.get('duration_ms', 0)
        
        # Extract artists
        artists = track_data.get('artists', [])
        artist_names = ', '.join([artist['name'] for artist in artists]) if artists else ''
        
        # Extract album
        album_data = track_data.get('album', {})
        album_name = album_data.get('name', '') if album_data else ''
        
        # Build Spotify URL
        spotify_url = track_data['external_urls']['spotify'] if track_data.get('external_urls') else ''
        
        # Create file name with track number
        file_name = f"{track_number:02d} - {track_name}"
        
        return {
            'spotify_url': spotify_url,
            'title': track_name,
            'artist': artist_names,
            'album': album_name,
            'track_number': track_number,  # Sequential number, not Spotify's inconsistent number
            'file_name': file_name,
            'duration_ms': duration_ms,
            'track_id': track_id
        }

