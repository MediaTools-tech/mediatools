import os
import subprocess
import re
import time
import platform
from tkinter import messagebox
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, List
import glob
import logging
from pathlib import Path


# Constants for timeout configuration
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

    # Add state update callbacks
    update_download_state: Optional[Callable] = None
    update_pause_state: Optional[Callable] = None
    update_stop_state: Optional[Callable] = None
    update_buttons_based_on_format: Optional[Callable] = None
    check_internet_connection: Optional[Callable] = None
    add_to_delete_list: Optional[Callable] = None
    set_pause_resume_state: Optional[Callable] = None
    exit_app: Optional[Callable] = None

    download_path_temp: str = ""
    pending_button_update: bool = False
    current_process: Optional[Any] = None
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
        # self.context.status_label_fg = "#68cdfe"

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

    def download_video(self, url):
        """Download a single video"""
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

                return
            else:
                self.context.exit_app()

        self.context.is_downloading = True
        self.context.current_download_url = url
        self.context.recent_url = url
        self.download_path = ""
        self.context.download_path_temp = ""

        # Update queue display immediately
        self.root.after(
            0,
            self.context.update_queue_display(fg=self.context.status_label_fg),
        )

        if self.context.is_resumed:
            self.root.after(
                0,
                lambda: self.context.update_status(
                    f"Resuming...{self.context.recent_url}",
                    fg=self.context.status_label_fg,
                ),
            )
        else:
            emoji = self.style_manager.get_emoji("find")
            emoji += " " if emoji else ""
            self.root.after(
                0,
                lambda: self.context.update_status(
                    f"{emoji}Fetching video info...{self.context.recent_url}",
                    fg=self.context.status_label_fg,
                ),
            )

        try:
            self.download(url)

            if self.context.pending_button_update:
                self.context.update_buttons_based_on_format()

        except Exception as e:
            self.root.after(
                0,
                lambda: self.context.update_status(
                    f"Download failed: {str(e)}", error=True
                ),
            )
            self.queue_manager.add_failed_url(url, str(e))
        finally:
            self.context.is_downloading = False
            self.root.after(
                0,
                self.context.update_queue_display(fg=self.context.status_label_fg),
            )

    def download(self, url):
        """Download cmd and execute cmd"""
        # Get current settings
        settings = self.settings
        self.percent_value = 0.0

        format_setting = self.settings.get(
            "stream_and_merge_format", "bestvideo+bestaudio/best-mkv"
        )

        # Define fallback chains based on user's format preference
        if format_setting == "b":
            format_fallback_chain = [
                ("b", None)  # Single attempt for 'b' format
            ]
        elif format_setting == "bestvideo+bestaudio/best-mkv":
            format_fallback_chain = [
                ("bestvideo+bestaudio/best", "mkv"),  # Primary: MKV merge
                ("bestvideo+bestaudio/best", "mp4"),  # Fallback: MP4 merge  
                ("b", None)                           # Final: Pre-merged
            ]
        elif format_setting == "bestvideo+bestaudio/best-mp4":
            format_fallback_chain = [
                ("bestvideo+bestaudio/best", "mp4"),  # Primary: MP4 merge
                ("b", None)                           # Fallback: Pre-merged
            ]
        else:
            # Default fallback for unknown formats
            format_fallback_chain = [
                ("bestvideo+bestaudio/best", "mkv"),
                ("bestvideo+bestaudio/best", "mp4"),
                ("b", None)
            ]

        if (
            not self.context.ffmpeg_status["is_ffmpeg_suite_available"]
            and format_setting != "b"
        ):
            self.context.update_status(
                "Ffmpeg Missing. Download now or Videos will be downloaded with sub-optimal setting: Format - b",
                error=True,
            )

            if self.custom_msg_box.custom_askyesno(
                self.root,
                "ffmpeg Missing",
                "Ffmpeg required for downloading best quality video\n\nPress 'Yes' to download missing Ffmpeg\nPress 'No' to use sub-optimal setting: Format - b",
                self.messagebox_font,
            ):

                self.context.update_status("")
                self.context.do_update_ffmpeg()
            else:
                self.settings.set("stream_and_merge_format", "b")
                self.settings.save_settings()

        # Remove old status frame if it exists
        if self.context.success_frame is not None:
            self.context.success_frame.destroy()

        if self.context.is_resumed:
            self.root.after(
                0,
                lambda: self.context.update_status(
                    f"Resuming...{self.context.recent_url}",
                    fg=self.context.status_label_fg,
                ),
            )
        else:
            emoji = self.style_manager.get_emoji("find")
            emoji += " " if emoji else ""
            self.root.after(
                0,
                lambda: self.context.update_status(
                    f"{emoji}Fetching video info...{self.context.recent_url}",
                    fg=self.context.status_label_fg,
                ),
            )

        # Update queue display immediately
        self.root.after(
            0,
            self.context.update_queue_display(fg=self.context.status_label_fg),
        )

        self.context.safe_title = "Unknown Video"  # Fallback title

        # settings = self.settings
        self.download_path = settings.get("downloads_dir")
        if settings.get("platform_specific_download_folders"):
            domains_list = re.split(
                r"[,\s]+", settings.get("subfolder_domains").strip()
            )
            site = next(
                (url_from for url_from in domains_list if url_from in url),
                "other",
            )
            self.download_path = os.path.join(
                settings.get("downloads_dir"), site.split(".", 1)[0]
            )

        self.context.download_path_temp = os.path.join(self.download_path, "temp")
        
        return_code = 1
        is_last_iteration = False

        try:
            for iteration, (stream_format, merge_format) in enumerate(format_fallback_chain):
                is_last_iteration = (iteration == len(format_fallback_chain) - 1)
                # print(stream_format, merge_format)
                if merge_format == "mkv":
                    self.context.set_pause_resume_state(False)
                else:
                    self.context.set_pause_resume_state(True)

                if iteration > 0:
                    self.status_text = f"Retrying with stream_format-{stream_format},  merge_format-{merge_format}"
                    # update_gui
                    self.root.after(
                        0,
                        lambda: self.context.update_status(
                            self.status_text,
                            percent=0,
                            fg=self.context.status_label_fg,
                        ),
                    )
                try:
                    cmd = [
                        self.context.ytdlp_path,
                        "--format",
                        stream_format
                        ]

                    if merge_format:
                        cmd.extend(["--merge-output-format", merge_format])

                    cmd.extend([
                        "--no-overwrites",
                        "--continue",
                        "--output",
                        "%(title)s-%(id)s.%(ext)s",
                        url,
                        "--limit-rate",
                        self.settings.get("download_speed"),
                        "--embed-thumbnail",
                        # "--convert-thumbnails", "jpg",
                        "--no-write-thumbnail",
                        "--restrict-filenames",
                        "--trim-filenames",
                        "100",
                        "--progress-template",
                        "%(progress._percent_str)s",
                        "--console-title",
                        "--newline",
                        "--yes-playlist",
                        "--ignore-errors",
                        "--no-abort-on-error",
                        "--sleep-interval",
                        "2",
                        "--max-sleep-interval",
                        "8",
                        "--retries",
                        "15",
                        "--fragment-retries",
                        "15",
                        "--retry-sleep",
                        "3",
                        "--socket-timeout",
                        "30",
                        "--extractor-retries",
                        "3",
                        "--force-keyframes-at-cuts",
                        "--paths",
                        f"home:{self.download_path}",
                        "--paths",
                        f"temp:{self.context.download_path_temp}",
                    ])


                    # Add cookies if enabled
                    cookies_cmd = self.settings.get_cookies_cmd()
                    if cookies_cmd:
                        cmd.extend(cookies_cmd)

                    # Add download archive if enabled
                    archive_enabled = self.settings.get("enable_download_archive")
                    if archive_enabled:
                        archive_path = self.settings.get(
                            "download_archive_path", "downloaded.txt"
                        )
                        cmd.extend(["--download-archive", archive_path])

                    if self.context.ffmpeg_status["is_ffmpeg_suite_downloaded"]:
                        cmd.extend(
                            [
                                "--ffmpeg-location",
                                os.path.dirname(self.context.ffmpeg_path),
                            ]
                        )

                    cmd = [c for c in cmd if c]

                    # Check for connection
                    while True:
                        if self.context.check_internet_connection():
                            break
                        else:
                            if self.custom_msg_box.custom_askyesno(
                                self.root,
                                "Waiting for Connection",
                                "No internet connection detected!\nConnect to the internet to continue.\n\nClick 'Yes' to retry. Click 'No' to Exit",
                                self.messagebox_font,
                            ):
                                continue
                            else:
                                self.context.exit_app()
                                return

                    self.context.video_index = None
                    self.context.total_videos = None
                    self.context.is_playlist = False
                    self.context.files_downloaded = 0
                    self.context.final_filename_check = ""
                    self.files_skipped_prev = 0
                    self.files_skipped_current = 0

                    # Your existing code with cross-platform window hiding:
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

                    process = subprocess.Popen(cmd, **process_kwargs)

                    # Store process reference for pause/resume/stop control
                    self.context.current_process = process

                    import inspect
                    for line in process.stdout:
                        # Check for stop condition - check more frequently
                        if self.context.is_stopped:
                            # print("Stop condition detected in download loop")
                            break

                        if self.context.is_paused:
                            # print("Pause condition detected in download loop")
                            break

                        if self.context.is_exit:
                            # print("Exit condition detected in download loop")
                            break

                        # Check if process has been terminated externally
                        if process.poll() is not None:
                            print("Process terminated externally")
                            break

                        line = line.strip()
                        if line.startswith("DownloadedFile:"):
                            self.context.final_filename_check = line.split(
                                "DownloadedFile:", 1
                            )[1].strip()
                        else:
                            match = re.search(
                                r"(.*\.(?:mp4|mkv|webm|avi|mov|flv|m4v|wmv))",
                                line.strip().strip('"').strip("'"),
                                re.IGNORECASE,
                            )
                            if match:
                                full_path = match.group(1)
                                self.context.final_filename_check = os.path.basename(
                                    full_path
                                )  # Just the filename with extension

                        # Detect playlist info - try multiple patterns
                        playlist_patterns = [
                            r"Downloading video (\d+) of (\d+)",
                            r"[download] Downloading video (\d+) of (\d+)",
                            r"Downloading item (\d+) of (\d+)",
                        ]

                        for pattern in playlist_patterns:
                            match = re.search(pattern, line)
                            if match:
                                self.context.video_index = int(match.group(1))
                                self.context.total_videos = int(match.group(2))
                                self.context.is_playlist = True
                                break

                        # Detect title from multiple possible sources
                        title_indicators = [
                            "Destination:",
                            "[download]",
                            "Extracting URL:",
                        ]
                        for indicator in title_indicators:
                            if indicator in line and (
                                "Destination:" in line or "Extracting URL:" in line
                            ):
                                if "Destination:" in line:
                                    parts = line.split("Destination:", 1)
                                    if len(parts) > 1:
                                        filename = parts[1].strip()
                                        self.context.safe_title = os.path.basename(filename)
                                elif "Extracting URL:" in line:
                                    # Try to extract title from URL extraction line
                                    if ":" in line:
                                        potential_title = line.split(":")[-1].strip()
                                        if potential_title and len(potential_title) < 100:
                                            self.context.safe_title = potential_title
                                break

                        # Update GUI with current video info and queue status
                        if (
                            self.context.safe_title
                            and self.context.safe_title != "Unknown Video"
                        ):
                            display_title = self.context.safe_title[:65]
                            queue_count = self.queue_manager.get_queue_count()
                            if self.context.is_resumed:
                                if (
                                    self.context.is_playlist
                                    and self.context.video_index
                                    and self.context.total_videos
                                ):
                                    self.status_text = f"{self.style_manager.get_emoji('loading')} Video {self.context.video_index}/{self.context.total_videos}: {display_title}"
                                else:
                                    self.status_text = f"{self.style_manager.get_emoji('loading')} Resuming: {display_title}"
                            else:
                                if (
                                    self.context.is_playlist
                                    and self.context.video_index
                                    and self.context.total_videos
                                ):
                                    self.status_text = f"{self.style_manager.get_emoji('loading')} Video {self.context.video_index}/{self.context.total_videos}: {display_title}"
                                else:
                                    self.status_text = f"{self.style_manager.get_emoji('loading')} Preparing to download...: {display_title}"

                            if self.context.is_resumed:
                                self.root.after(
                                    0,
                                    lambda: self.context.update_status(
                                        self.status_text, fg=self.context.status_label_fg
                                    ),
                                )
                            else:
                                self.root.after(
                                    0,
                                    lambda: self.context.update_status(
                                        self.status_text,
                                        percent=0,
                                        fg=self.context.status_label_fg,
                                    ),
                                )

                        # Handle skipped files
                        skip_indicators = [
                            "has already been downloaded",
                            "File is already present and --no-overwrites is enabled",
                            "Skipping",
                            "already in archive",
                        ]

                        for skip_indicator in skip_indicators:
                            if skip_indicator in line:
                                self.files_skipped_current += 1
                                display_title = (
                                    self.context.safe_title[:65]
                                    if self.context.safe_title
                                    else "Previously Downloaded Video"
                                )
                                queue_count = self.queue_manager.get_queue_count()

                                if (
                                    self.context.is_playlist
                                    and self.context.video_index
                                    and self.context.total_videos
                                ):
                                    self.status_text = f"↷ Video {self.context.video_index}/{self.context.total_videos}: Skipped - {display_title}"
                                else:
                                    self.status_text = f"↷ Skipped: {display_title} (check if already exists in downloads folder)"

                                # update_gui(percent=100, text=self.status_text)
                                self.root.after(
                                    0,
                                    lambda: self.context.update_status(
                                        self.status_text,
                                        percent=0,
                                        fg=self.context.status_label_fg,
                                    ),
                                )
                                # Skipped files - Clean up incomplete files
                                if hasattr(self.context, 'safe_title') and self.context.safe_title:
                                    self.context.final_filename_check = self.context.safe_title
                                    # base_name = self.context.safe_title.split(".")[0].strip()
                                    base_name = self.get_base_name_from_ytdlp_file(self.context.safe_title)
                                    self.cleanup_video_leftovers(base_name, self.context.download_path_temp)

                                break

                        # Detect progress
                        if line and re.match(r"^\s*\d+\.\d+%\s*$", line):
                            percent_str = line.replace("%", "").strip()
                            try:
                                self.percent_value = float(percent_str)
                                if 0.0 <= self.percent_value <= 100.0:

                                    if self.context.is_resumed:
                                        self.context.is_resumed = False
                                    if self.percent_value > self.context.progress_bar.value:
                                        self.context.progress_bar.value = self.percent_value
                                    display_title = (
                                        self.context.safe_title[:65]
                                        if self.context.safe_title
                                        else "Video"
                                    )
                                    queue_count = self.queue_manager.get_queue_count()

                                    if (
                                        self.context.is_playlist
                                        and self.context.video_index
                                        and self.context.total_videos
                                    ):
                                        self.status_text = f"↓ Video {self.context.video_index}/{self.context.total_videos}: {display_title} - {self.percent_value}%"
                                    else:
                                        self.status_text = (
                                            f"↓ {display_title} - {self.percent_value}%"
                                        )

                                    # update_gui(percent=self.percent_value, text=self.status_text)
                                    self.root.after(
                                        0,
                                        lambda: self.context.update_status(
                                            self.status_text,
                                            percent=self.percent_value,
                                            fg=self.context.status_label_fg,
                                        ),
                                    )
                            except ValueError:
                                pass

                        # Count successful downloads
                        if "[download] 100%" in line or "Deleting original file" in line:
                            self.context.files_downloaded += 1

                    # Wait for completion and handle exit codes properly
                    return_code = process.wait()

                    # Clear process reference
                    self.context.current_process = None
                    # Check if download was stopped
                    if self.context.is_stopped or self.context.is_paused:
                        # print("Download was pause/stopped, exiting download method")
                        if self.root.winfo_exists():
                            self.root.after(
                                0,
                                lambda: self.context.update_status(
                                    f"{self.style_manager.get_emoji('stop')}  Download stopped",
                                    percent=self.context.progress_bar.value,
                                    fg=self.context.status_label_fg,
                                ),
                            )
                        # Clear URL variables when stopped
                        self.context.current_download_url = None
                        self.context.paused_url = None
                        return
                    
                    if return_code == 0: 
                        break                    

                    if return_code not in [0] and is_last_iteration:
                        error_msg = f"Download failed (code {return_code})"
                        self.queue_manager.add_failed_url(url, error_msg)
                        raise Exception(error_msg)

                finally:
                    # Ensure process is cleaned up
                    if process and process.poll() is None:
                        try:
                            process.terminate()
                        except:
                            pass

                    if return_code == 0 or is_last_iteration:
                        if self.context.is_playlist:
                            if self.context.is_stopped:
                                self.status_text = f"{self.style_manager.get_emoji('stop')} Download stopped: {self.context.recent_url}"
                                self.context.is_stopped = False                        
                            elif self.context.is_paused:
                                self.status_text = f"{self.style_manager.get_emoji('pause')} Download paused: {self.context.recent_url} - {self.percent_value}%"
                            elif self.context.is_after_stopped:
                                self.status_text = f"{self.style_manager.get_emoji('stop')} Download stopped: {self.context.recent_url}"
                                self.context.is_after_stopped = False
                            else:
                                self.status_text = f"✓ Playlist complete: Downloaded {self.context.total_videos-self.files_skipped_current} videos"
                                self.queue_manager.remove_url()
                        else:
                            if self.files_skipped_current > self.files_skipped_prev:
                                self.status_text = "Skipped. Check if already downloaded"
                                self.queue_manager.remove_url()
                                self.files_skipped_prev = self.files_skipped_current
                                if self.check_files_exist_by_base(f"{self.context.final_filename_check.rsplit('.', 1)[0]}", self.download_path):
                                    # base_name = self.context.final_filename_check.rsplit('.', 1)[0]
                                    base_name = self.get_base_name_from_ytdlp_file(self.context.final_filename_check)
                                    self.context.add_to_delete_list(base_name, self.context.download_path_temp)

                            else:
                                if self.context.is_stopped:
                                    self.status_text = f"{self.style_manager.get_emoji('stop')} Download stopped: {self.context.recent_url}"
                                    self.context.is_stopped = False
                                elif self.context.is_paused:
                                    self.status_text = f"{self.style_manager.get_emoji('pause')} Download paused: {self.context.recent_url} - {self.percent_value}%"
                                elif self.context.is_after_stopped:
                                    self.status_text = f"{self.style_manager.get_emoji('stop')} Download stopped {self.context.recent_url}"
                                    self.context.is_after_stopped = False
                                else:
                                    self.status_text = "✓ Download complete"
                                    if self.check_files_exist_by_base(f"{self.context.final_filename_check.rsplit('.', 1)[0]}", self.download_path):
                                        # base_name = self.context.final_filename_check.rsplit('.', 1)[0]
                                        base_name = self.get_base_name_from_ytdlp_file(self.context.final_filename_check)
                                        self.context.add_to_delete_list(base_name, self.context.download_path_temp)

                                    self.queue_manager.remove_url()

                                queue_count = self.queue_manager.get_queue_count()

                        self.root.after(
                            0,
                            lambda: self.context.update_status(
                                self.status_text,
                                percent=self.context.progress_bar.value,
                                fg=self.context.status_label_fg,
                            ),
                        )
                        latest_downloaded_video = os.path.join(
                            self.download_path, self.context.final_filename_check
                        )

        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            self.queue_manager.add_failed_url(url, str(e))
            self.root.after(
                0, lambda: self.context.update_status(error_msg, error=True)
            )

        finally:
            # Clean up process reference
            if self.context.current_process:
                try:
                    if (
                        self.context.current_process.poll() is None
                    ):  # Process still running
                        self.context.current_process.terminate()
                        self.context.current_process.wait(
                            timeout=5
                        )  # Wait for termination
                except:
                    pass
                self.context.current_process = None
            self.context.is_downloading = False
            # Update queue display immediately
            self.root.after(
                0,
                self.context.update_queue_display(fg=self.context.status_label_fg),
            )

        self.rename_fully_downloaded_part_files(self.download_path)
        self.rename_fully_downloaded_part_files(self.context.download_path_temp)
        self.context.safe_title = ""

    def check_files_exist_by_base(self, base_name, folder_path):
        """Check if any files exist with this base name"""
        # print(os.path.join(folder_path, f"{base_name}"))
        pattern = os.path.join(folder_path, f"{base_name}.*")
        matching_files = glob.glob(pattern)
        return len(matching_files) > 0, matching_files

    def cleanup_video_leftovers(self, base_name, download_path):
        """Clean up incomplete files for a specific video that was skipped or failed"""
        import os
        import glob
        # import re
        
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
            if (file_name.endswith(('.temp.mkv', '.temp.mp4', '.part', '.ytdl')) or
                re.search(r'\.f\d+\..+', file_name) or  # Fragment files like .f401.mp4
                file_name in [f"{base_name}.webp", f"{base_name}.jpg", f"{base_name}.png"]):
                
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
        import os
        import glob
        import shutil
        
        try:
            # Normalize and validate paths
            download_path = os.path.abspath(os.path.normpath(download_path))
            main_download_path = os.path.abspath(os.path.normpath(self.download_path))
            
            # Ensure directories exist
            os.makedirs(main_download_path, exist_ok=True)
            
            pattern = os.path.join(download_path, "*.part")
            
            for part_file in glob.glob(pattern):
                try:
                    if self.is_video_complete(part_file):
                        self._process_completed_part_file(part_file, download_path, main_download_path)
                except Exception as e:
                    print(f"Error processing {part_file}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error in cleanup process: {e}")

    def _process_completed_part_file(self, part_file, source_path, dest_path):
        """Process a single completed part file"""
        import os
        import shutil
        
        filename = os.path.basename(part_file).replace('.part', '')
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
        thumbnail_extensions = ['.jpg', '.jpeg', '.png', '.webp']
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
                self.context.ffprobe_path,  # This should already be cross-platform
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                file_path
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
                timeout=10,
                **process_kwargs  # Your cross-platform subprocess settings
            )
            
            # Check if we got a valid duration
            return (result.returncode == 0 and 
                    result.stdout.strip() and 
                    float(result.stdout.strip()) > 0)
                    
        except (subprocess.TimeoutExpired, ValueError, OSError):
            return False

    def pause_download(self):
        """Pause the current download process"""
        if (
            self.context.current_process
            and self.context.is_downloading
            and not self.context.is_paused
            and not self.context.is_stopped
        ):
            try:
                self.stop_download("pause")
                
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
            not self.context.current_process
            or self.context.current_process.poll() is not None
        ):
            # messagebox.showinfo("Info", "No active download process to pause")
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No active download process to pause",
                self.messagebox_font,
            )

    def resume_download(self):
        """Resume the current download process"""
        if self.context.is_paused and not self.context.is_stopped:
            try:
                self.context.is_resumed = True
                self.context.is_paused = False

                self.context.update_status(
                    f"{self.style_manager.get_emoji('play')} Resuming download... {self.context.recent_url} {self.context.progress_bar.value}%",
                    percent=self.context.progress_bar.value,
                    fg=self.context.status_label_fg,
                )

                # Start queue processing if not already running
                if not self.context.is_downloading:
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
            not self.context.current_process
            or self.context.current_process.poll() is not None
        ):
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No active download process to resume",
                self.messagebox_font,
            )

    def stop_download(self, stop_condition="stop"):
        """Stop the current download process"""
        if not self._should_stop_download():
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No active download process to pause/stop",
                self.messagebox_font,
            )
            return

        current_url = self.context.current_download_url

        if self.context.is_paused and stop_condition == "stop":
            self.context.is_after_stopped = True
            self.context.is_paused = False
            self.queue_manager.remove_url(current_url)
            self.context.update_status(
                f"{self.style_manager.get_emoji('stop')} Download stopped: {self.context.recent_url} {self.context.progress_bar.value}% ",
                percent=0,
                fg=self.context.status_label_fg,
            )
            if hasattr(self.context, 'safe_title') and self.context.safe_title:
                # base_name = self.context.safe_title.split(".")[0].strip()
                base_name = self.get_base_name_from_ytdlp_file(self.context.safe_title)
                self.cleanup_video_leftovers(base_name, self.context.download_path_temp)
                self.context.add_to_delete_list(base_name, self.context.download_path_temp)
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
        if self.context.current_process and self.context.is_downloading:
            try:
                self.stop_download_core()
            except:
                pass

        # Clear process reference and state
        self._reset_download_state()

        if stop_condition == "pause":
            self.context.update_status(
                f"{self.style_manager.get_emoji('stop')} Download paused: {self.context.recent_url} {self.context.progress_bar.value}%",
                percent=self.context.progress_bar.value,
                fg=self.context.status_label_fg,
            )
            print("Download pause completed")
        else:
            self.context.update_status(
                f"{self.style_manager.get_emoji('stop')} Download stopped: {self.context.recent_url} {self.context.progress_bar.value}%",
                percent=0,
                fg=self.context.status_label_fg,
            )
            print("Download stop completed")

        if stop_condition == "stop":
            # self.context.is_after_stopped = True
            if hasattr(self.context, 'safe_title') and self.context.safe_title:
                # base_name = self.context.safe_title.split(".")[0].strip()
                base_name = self.get_base_name_from_ytdlp_file(self.context.safe_title)
                self.cleanup_video_leftovers(base_name, self.context.download_path_temp)
                self.context.add_to_delete_list(base_name, self.context.download_path_temp)
            
            self.context.start_queue_processing()

    def _should_stop_download(self):
        """Check if download should be stopped"""
        return (
            self.context.is_paused
            and not self.context.current_process
            and not self.context.is_downloading
        ) or (self.context.current_process and self.context.is_downloading)

    def _reset_download_state(self):
        """Reset all download state variables"""
        self.context.current_process = None
        self.context.is_downloading = False
        self.context.current_download_url = None

    def _check_psutil_availability(self):
        """Check if psutil is available without raising ImportError"""
        try:
            import psutil

            return True
        except ImportError:
            return False

    def stop_download_core(self):
        """Stop the current download process with cross-platform process tree termination"""
        if not self._validate_process_state():
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No active download process to stop",
                self.messagebox_font,
            )
            return

        for attempt in range(MAX_TERMINATION_ATTEMPTS):
            try:
                logger.info(f"Attempt {attempt + 1} to terminate download process")

                if IS_WINDOWS:
                    success = self._terminate_windows()
                else:
                    success = self._terminate_unix()

                if success:
                    logger.info("Download process terminated successfully")
                    break

            except Exception as e:
                logger.error(f"Termination attempt {attempt + 1} failed: {e}")
                if attempt == MAX_TERMINATION_ATTEMPTS - 1:
                    self._handle_termination_failure(e)

        self._cleanup_after_termination()

    def _validate_process_state(self):
        """Validate if there's a process that needs termination"""
        return (
            self.context.current_process
            and self.context.is_downloading
            and self.context.current_process.poll() is None
        )  # Process is still running

    def _terminate_windows(self):
        """Windows-specific process termination"""
        logger.info("Terminating process tree on Windows...")

        # Method 1: Try Windows API first (most reliable)
        if self._terminate_with_windows_api():
            return True

        # Method 2: Try taskkill
        if self._terminate_with_taskkill():
            return True

        # Method 3: Fallback to psutil
        if self._check_psutil_availability():
            if self._terminate_with_psutil():
                return True

        # Method 4: Final basic fallback
        return self._terminate_basic()

    def _terminate_with_windows_api(self):
        """Use Windows API for process termination"""
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(
                0x0001, False, self.context.current_process.pid
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

    def _terminate_with_taskkill(self):
        """Use taskkill for process termination on Windows"""
        try:
            result = subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(self.context.current_process.pid),
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

    def _terminate_unix(self):
        """Unix-like systems (Linux/Mac) process termination"""
        logger.info("Terminating process tree on Unix/Linux/Mac...")

        # Method 1: Process group termination
        if self._terminate_process_group():
            return True

        # Method 2: psutil fallback
        if self._terminate_with_psutil():
            return True

        # Method 3: Basic fallback
        return self._terminate_basic()

    def _terminate_process_group(self):
        """Terminate entire process group on Unix systems"""
        try:
            import signal

            # Get process group ID
            pgid = os.getpgid(self.context.current_process.pid)
            logger.info(f"Terminating process group {pgid}")

            # Send SIGTERM to entire process group
            os.killpg(pgid, signal.SIGTERM)

            # Wait for graceful termination
            try:
                self.context.current_process.wait(timeout=TIMEOUT_GRACEFUL)
                logger.info("Process group terminated with SIGTERM")
                return True
            except subprocess.TimeoutExpired:
                logger.warning("SIGTERM timeout, sending SIGKILL to process group")
                # Force kill entire process group
                os.killpg(pgid, signal.SIGKILL)
                try:
                    self.context.current_process.wait(timeout=TIMEOUT_FORCE)
                    logger.info("Process group killed with SIGKILL")
                    return True
                except subprocess.TimeoutExpired:
                    logger.error("Process group still running after SIGKILL")

        except (OSError, AttributeError, ProcessLookupError) as e:
            logger.warning(f"Process group termination failed: {e}")

        return False

    def _terminate_with_psutil(self):
        """Fallback method using psutil for process termination"""
        try:
            import psutil

            parent = psutil.Process(self.context.current_process.pid)
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

    def _terminate_basic(self):
        """Basic fallback termination method"""
        try:
            # Try graceful termination first
            self.context.current_process.terminate()
            try:
                self.context.current_process.wait(timeout=TIMEOUT_GRACEFUL)
                logger.info("Process terminated (basic fallback)")
                return True
            except subprocess.TimeoutExpired:
                # Force kill if graceful fails
                self.context.current_process.kill()
                try:
                    self.context.current_process.wait(timeout=TIMEOUT_FORCE)
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
            '.part',
            '.ytdl',
            '.temp.mkv',
            '.temp.mp4',
            '.temp.webm',
            '.mkv',
            '.mp4',
            '.webm',
            '.webp',
            '.jpg',
            '.jpeg',
            '.png',
        ]
        
        # Keep stripping until no more matches
        changed = True
        while changed:
            changed = False
            for ext in extensions_to_strip:
                if filename.lower().endswith(ext):
                    filename = filename[:-len(ext)]
                    changed = True
                    break
        
        # Remove yt-dlp format codes (e.g., .f401, .f251-9)
        # Pattern matches: .f followed by digits, optionally followed by -digits
        filename = re.sub(r'\.[f]\d+(-\d+)?$', '', filename, flags=re.IGNORECASE)
        
        return filename
