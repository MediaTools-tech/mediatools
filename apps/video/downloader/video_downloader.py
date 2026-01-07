from mediatools.video.downloader import __version__
VERSION_URL = "https://raw.githubusercontent.com/MediaTools-tech/mediatools/main/apps/video/downloader/version.txt"
DOWNLOAD_PAGE = "https://mediatools.tech/video/downloader.html"
import os
import re
import sys
import json
import subprocess
import threading
import requests
import platform
import socket
import glob
import time
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.request import urlopen
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Set
from urllib.parse import urlparse

# from queue_manager import queue_manager
from mediatools.video.downloader.core.shortcut_creator import first_run_setup
from mediatools.video.downloader.core.settings_manager import SettingsManager
from mediatools.video.downloader.utils.tools import FFmpegTool, YtdlpTool, SpotdlTool, DenoTool
from mediatools.video.downloader.core.queue_manager import QueueManager
from mediatools.video.downloader.core.download_service import (
    DownloadService,
    DownloadContext,
)
from mediatools.video.downloader.gui.theme_manager import ThemeManager, GUIContext
from mediatools.video.downloader.gui.settings_gui import SettingsGUIContext
from mediatools.video.downloader.compat.platform_style_manager import (
    PlatformStyleManager,
)
from mediatools.video.downloader.gui.custom_message_box import CustomMessageBox

from threading import Event
# Configure logging
import logging

logger = logging.getLogger(__name__)

# Determine platform
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


class VideoDownloaderApp:
    def __init__(self):
        self.root = tk.Tk()
        self._initialize_core_components()
        self._initialize_managers_and_tools()
        self._initialize_contexts()
        self._initialize_services_and_gui()
        self._perform_startup_checks()

    def _initialize_core_components(self):
        """Initialize core application settings and attributes."""
        self.session_check_completed = False   
        self.settings = self.initialize_settings()
        first_run_setup(self.settings)

        self.is_downloading = False
        self.is_updating = False
        self.latest_downloaded_video = None
        self.success_frame = None
        self.safe_title = "Unknown Video"
        self.video_index = None
        self.total_videos = None
        self.files_downloaded = 0
        self.final_filename_check = ""
        self.is_playlist = False
        self.recent_url = ""
        self.download_path = ""
        self.download_path_temp = ""
        self.current_process = None
        self.current_download_url = None
        self.paused_url = None
        self.is_paused = False
        self.is_resumed = False
        self.is_stopped = False
        self.is_after_stopped = False
        self.download_thread = None
        self.stopped_downloads_to_be_deleted = []
        self.stopdl_process = None
        self.spotdl_credential_warning = False
        self.is_exit = False
        self.ffmpeg_update_running = False
        self.cancel_spotdl_event = threading.Event()
        self.custom_msg_box = CustomMessageBox()
        self.status_label_fg = "#6c757d"
        self._setup_subprocess_kwargs()

    def _initialize_managers_and_tools(self):
        """Initialize managers and tool handlers."""
        self.ffmpeg_tool = FFmpegTool(self.settings)
        self.ytdlp_tool = YtdlpTool(self.settings)
        self.spotdl_tool = SpotdlTool(self.settings)
        self.deno_tool = DenoTool(self.settings)
        self.style_manager = PlatformStyleManager()
        self.q_manager = QueueManager(self.style_manager, self.open_queue_file, self.root)

        self.ffmpeg_status = self.ffmpeg_tool.get_ffmpeg_status()
        self.current_version_ytdlp = "Current version unkown"
        self.latest_version_ytdlp = "Latest version unknown"

        # if self.should_check_ytdlp_spotdl_updates():
        #     self.ytdlp_status = self.ytdlp_tool.get_ytdlp_status()
        #     self.spotdl_status = self.spotdl_tool.get_spotdl_status()
        #     self.ytdlp_path = self.ytdlp_status["ytdlp_path"]
        #     self.spotdl_path = self.spotdl_status["spotdl_path"]
        # else:
        #     self.ytdlp_path = self.ytdlp_tool.get_ytdlp_path()
        #     self.spotdl_path = self.spotdl_tool.get_spotdl_path()
        self.ytdlp_path = self.ytdlp_tool.get_ytdlp_path()
        self.spotdl_path = self.spotdl_tool.get_spotdl_path()

        # if self.should_check_deno_update():
        #     self.deno_status = self.deno_tool.get_deno_status()
        #     self.deno_path = self.deno_status["deno_path"]
        # else:
        #     self.deno_path = self.deno_tool.get_deno_path()
        self.deno_path = self.deno_tool.get_deno_path()


        self.bin_dir = self.settings.get("bin_dir")
        self.ffmpeg_path = self.ffmpeg_status["ffmpeg_path"]
        self.ffprobe_path = self.ffmpeg_status["ffprobe_path"]

    def _initialize_contexts(self):
        """Create and configure all context objects."""
        self.download_context = DownloadContext(
            download_folder=self.settings.get("downloads_dir"),
            update_status=self.update_status,
            update_queue_display=self.update_queue_display,
            gui_after=self.root.after,
            start_queue_processing=self.start_queue_processing,
            do_update_yt_dlp=self.do_update_yt_dlp,
            do_update_ffmpeg=self.do_update_ffmpeg,
            do_update_spotdl=self.do_update_spotdl,
            check_internet_connection=self.check_internet_connection,
            add_to_delete_list=self.add_to_delete_list,
            pause_resume_disable=self.pause_resume_disable,
            check_spotify_credentials_warning=self.check_spotify_credentials_warning,
            hide_spotify_credentials_warning=self.hide_spotify_credentials_warning,
            exit_app=self.exit_app,
            download_path=self.download_path,
            download_path_temp=self.download_path_temp,
            stopdl_process=self.stopdl_process,
            current_process=self.current_process,
            is_downloading=self.is_downloading,
            is_stopped=self.is_stopped,
            is_paused=self.is_paused,
            is_resumed=self.is_resumed,
            is_exit=self.is_exit,
            is_after_stopped=self.is_after_stopped,
            current_download_url=self.current_download_url,
            paused_url=self.paused_url,
            safe_title=self.safe_title,
            final_filename_check=self.final_filename_check,
            video_index=self.video_index,
            total_videos=self.total_videos,
            is_playlist=self.is_playlist,
            files_downloaded=self.files_downloaded,
            ytdlp_path=self.ytdlp_path,
            ffmpeg_path=self.ffmpeg_path,
            ffprobe_path=self.ffprobe_path,
            spotdl_path=self.spotdl_path,
            ffmpeg_status=self.ffmpeg_status,
            success_frame=self.success_frame,
            recent_url=self.recent_url,
            stopped_downloads_to_be_deleted=self.stopped_downloads_to_be_deleted,
            progress_bar=None,
            status_label_fg=None,
            download_type="video",
            cancel_spotdl_event=self.cancel_spotdl_event,
        )

        self.settings_gui_context = SettingsGUIContext(apply_theme_callabck=self.apply_theme)

        self.gui_context = GUIContext(
            progress_frame=None,
            progress_bar=None,
            status_label=None,
            status_label_fg=self.status_label_fg,
            queue_status_label=None,
            url_entry=None,
            url_var=None,
            buttons=None,
            add_url_to_queue=self.add_url_to_queue,
            pause_download_callback=None,
            resume_download_callback=None,
            stop_download_callback=None,
            update_tools=self.update_tools,
            play_latest_video=self.play_latest_video,
            open_folder=self.open_folder,
            open_failed_url_file=self.open_failed_url_file,
            open_queue_file=self.open_queue_file,
            open_settings_gui=self.open_settings_gui,
            exit_app=self.exit_app,
        )

    def _initialize_services_and_gui(self):
        """Initialize services and the main graphical user interface."""
        self.download_service = DownloadService(
            self.root,
            self.q_manager,
            self.settings,
            self.style_manager,
            self.custom_msg_box,
            self.download_context,
        )

        self.theme_manager = ThemeManager(
            self.root,
            self.q_manager,
            self.settings,
            self.style_manager,
            self.download_context,
            self.gui_context,
        )

        self.gui_context.pause_download_callback = self.download_service.pause_download
        self.gui_context.resume_download_callback = self.download_service.resume_download
        self.gui_context.stop_download_callback = self.download_service.stop_download

        self.theme_manager.setup_gui()

        self.download_context.progress_bar = self.gui_context.progress_bar
        self.q_manager.set_gui_context(self.gui_context)

        # Initialize fonts
        self.button_font = self._get_font("button", ("Arial", 9))
        self.label_font = self._get_font("label", ("Arial", 10))
        self.messagebox_font = self._get_font("messagebox", ("Arial", 10))

        # Initialize warning labels
        self.warning_label = tk.Label(
            self.root,
            text="",
            fg="#000000",
            font=(self.label_font[0], self.label_font[1] - 1),
            bg=self.root.cget("bg"),
        )
        self.warning_label_bottom = tk.Label(
            self.root,
            text="Video Downloads - Pause/Resume supported only for: Format - bestvideo+bestaudio/best-mkv",
            fg="#000000",
            font=(self.label_font[0], self.label_font[1] - 1),
            bg=self.root.cget("bg"),
        )

    def hide_spotify_credentials_warning(self):
        """Hide the Spotify credentials warning label."""
        self.warning_label.place_forget()
        self.spotdl_credential_warning = False

    def _get_font(self, font_name, fallback):
        """Safely get font configuration from the style manager."""
        try:
            font_config = self.style_manager.get_font_config(font_name)
            return (font_config["family"], font_config["size"])
        except Exception:
            return fallback

    def initialize_settings(self):
        """Initialize settings with robust fallback chain"""
        try:
            settings = SettingsManager()
            return settings

        except Exception as e:
            print(f"SettingsManager failed: {e}")

    def pause_resume_disable(self, disable_pause_resume_flag):
        """Enable or disable pause/resume buttons"""
        state = "disabled" if disable_pause_resume_flag else "normal"

        # Show/hide warning
        if disable_pause_resume_flag:
            self.warning_label_bottom.place(x=162, y=387)
            self.warning_label_bottom.tkraise()
        else:
            self.warning_label_bottom.place_forget()  # Hide the warning

        try:
            if hasattr(self.gui_context, "buttons"):
                buttons = self.gui_context.buttons

                if "pause_btn" in buttons and state == "disabled":
                    buttons["pause_btn"].config(state=state)
                else:
                    buttons["pause_btn"].config(
                        state=state,
                        text=f"{self.style_manager.get_emoji('pause')} Pause",
                    )
                if "resume_btn" in buttons and state == "disabled":
                    buttons["resume_btn"].config(state=state)
                else:
                    buttons["resume_btn"].config(
                        state=state,
                        text=f"{self.style_manager.get_emoji('play')} Resume",
                    )

        except Exception as e:
            print(f"Error updating button states: {e}")

    def add_url_to_queue(self, download_type="video"):
        """Add URL to download queue"""
        url = self.gui_context.url_var.get().strip()
        # check if queue.txt updated externally
        if not url:
            self.start_queue_processing()
            return
        elif not self.is_valid_url(url):
            self.custom_msg_box.custom_showwarning(
                self.root,
                "Warning",
                "Please enter a valid URL",
                self.messagebox_font,
            )
            return

        if self.q_manager.add_url(url, download_type):
            self.gui_context.url_var.set("")  # Clear entry field
            self.update_queue_display(self.gui_context.status_label_fg)
            self.start_queue_processing()
        else:
            # messagebox.showerror("Error", "Failed to add URL to queue")
            self.custom_msg_box.custom_showerror(
                self.root, "Error", "Failed to add URL to queue", self.messagebox_font
            )
            
    def check_spotify_credentials_warning(self, url_under_Process):
        self.warning_label.place_forget()  # Hide the warning
        spotify_credentials = self.settings.get("spotify_client_id") and self.settings.get("spotify_client_secret")
        if "spotify.com" in url_under_Process and not spotify_credentials:
            self.spotdl_credential_warning = True
            text = "To download Spotify url (metadata), add Spotify credentials in settings. Check the User Guide."
            self.warning_label = tk.Label(
                self.root,
                text=text,
                fg="#000000",
                font=(self.label_font[0], self.label_font[1] - 1),
                bg=self.root.cget("bg"),
            )
            self.warning_label.place(x=125, y=12)
            self.warning_label.tkraise()

        elif "spotify.com" in url_under_Process and "/playlist/" in url_under_Process and \
            spotify_credentials and not self.settings.get("enable_spotify_playlist"):
            self.spotdl_credential_warning = True
            text = "For full Spotify playlist download support (metadata), enable the Spotify playlist option in Settings. Check the User Guide."
            self.warning_label = tk.Label(
                self.root,
                text=text,
                fg="#000000",
                font=(self.label_font[0], self.label_font[1] - 1),
                bg=self.root.cget("bg"),
            )
            self.warning_label.place(x=90, y=12)
            self.warning_label.tkraise()



    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def start_queue_processing(self):
        """Start processing the download queue"""
        if (
            not self.download_context.is_downloading
            and self.q_manager.has_queued_urls()
        ):
            threading.Thread(target=self.process_queue, daemon=True).start()

    def update_queue_display(self, fg="#1231F9"):
        """Update the status label with queue information"""
        queue_count = self.q_manager.get_queue_count()
        fg = self.gui_context.status_label_fg
        if queue_count > 0:
            if self.download_context.is_downloading:
                status_text = f"Download in progress. URLs in queue: {queue_count}."
            else:
                status_text = f"URLs in queue: {queue_count}. Ready to start."
            self.root.after(
                0,
                lambda: self.gui_context.queue_status_label.config(
                    text=status_text, fg=fg
                ),
            )
        elif not self.download_context.is_downloading:
            self.root.after(
                0,
                lambda: self.gui_context.queue_status_label.config(text="", fg="black"),
                # lambda: self.gui_context.queue_status_label.config(text=""),
            )

    def process_queue(self):
        """Process all URLs in the download queue"""
        # Add a lock to prevent multiple queue processing threads
        if (
            hasattr(self, "_queue_processing_lock")
            and self._queue_processing_lock.locked()
        ):
            return

        if not hasattr(self, "_queue_processing_lock"):
            self._queue_processing_lock = threading.Lock()

        with self._queue_processing_lock:
            while (
                self.q_manager.has_queued_urls()
                and not self.download_context.is_downloading
                and not self.download_context.is_paused
            ):
                url, download_type = self.q_manager.get_next_url()
                if url:
                    self.download_context.download_type = download_type
                    self.download_service.download_video(url, download_type)

    def update_status(
        self,
        text,
        percent=None,
        fg=None,
        fg_error="#CD1616",
        error=False,
    ):
        """Update status display"""
        fg = fg or self.gui_context.status_label_fg

        def update_gui():
            if percent is not None:
                self.download_context.progress_bar.value = percent
            self.gui_context.status_label.config(
                text=text, fg=fg_error if error else fg
            )

        self.root.after(0, update_gui)

    def update_progress(self, percent):
        """Update progress bar"""
        self.root.after(
            0, lambda: setattr(self.download_context.progress_bar, "value", percent)
        )

    def open_settings_gui(self):
        """Open config file or settings GUI"""
        # Add debug to see all available settings
        try:
            from mediatools.video.downloader.gui.settings_gui import SettingsWindow

            settings_window = SettingsWindow(
                self.root,
                self.settings,
                self.style_manager,
                self.custom_msg_box,
                self.settings_gui_context,
            )
            settings_window.open()
        except Exception as e:
            print(f"Failed to open settings gui. Error code: {e}")
            if settings_window is not None:
                settings_window.window.destroy()

            # Fallback to opening settings.json file
            config_path = self.get_app_root() / "data" / "settings.json"
            if config_path.exists():
                self.open_file_safely(config_path)
                self.custom_msg_box.custom_showinfo(
                    self.root,
                    "Info",
                    "Failed to open settings gui\nUse settings.json",
                    self.messagebox_font,
                )
            else:
                self.custom_msg_box.custom_showinfo(
                    self.root,
                    "Info",
                    "Config file not found",
                    self.messagebox_font,
                )

    def _handle_settings_fallback(self, error_msg):
        """Handle when settings GUI is unavailable"""
        message = f"{error_msg}\n\nWould you like to:\n• Reset to defaults\n• View current settings\n• Open data folder"

        # Offer user choices instead of just opening config.py
        choice = self.custom_msg_box.custom_askyesnocancel(
            self.root, "Settings Options", message, self.messagebox_font
        )

        if choice is True:  # Reset to defaults
            self.settings.reset_to_defaults()
            self.custom_msg_box.custom_showinfo(
                self.root, "Success", "Settings reset to defaults", self.messagebox_font
            )
        elif choice is False:  # View current settings
            self._show_settings_info()
        # Cancel - do nothing

    def _handle_settings_error(self, error_msg):
        """Handle settings errors gracefully"""
        self.custom_msg_box.custom_showerror(
            self.root,
            "Settings Error",
            f"{error_msg}\n\nTry restarting the application.",
            self.messagebox_font,
        )

    def _show_settings_info(self):
        """Show current settings in a simple dialog"""
        settings_text = "Current Settings:\n\n"
        for key, value in self.settings.get_all().items():
            settings_text += f"{key}: {value}\n"

        # Create simple text window or message box
        self.custom_msg_box.custom_showinfo(
            self.root, "Current Settings", settings_text, self.messagebox_font
        )

    def open_queue_file(self, queue_path=None):
        """Open queue file"""
        if not queue_path:
            queue_path = self.settings.get("queue_file")
        if queue_path and os.path.exists(queue_path):
            self.open_file_safely(Path(queue_path))
        else:
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "Queue file not found or queue system disabled",
                self.messagebox_font,
            )

    def open_failed_url_file(self):
        """Open failed URLs file"""
        failed_path = self.settings.get("failed_url_file")
        if failed_path and os.path.exists(failed_path):
            self.open_file_safely(Path(failed_path))
        else:
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "Failed URL file not found or tracking disabled",
                self.messagebox_font,
            )

    def open_file_safely(self, file_path):
        file_path = Path(file_path).resolve()
        """Platform-specific safe file opening"""
        try:
            if os.name == "nt":  # Windows
                # Use Notepad explicitly (never executes Python files)
                subprocess.Popen(["notepad", file_path])

            elif sys.platform == "darwin":  # macOS
                # Use TextEdit explicitly
                subprocess.Popen(["open", "-a", "TextEdit", file_path])

            # else:  # Linux
            #     # Try safe GUI editors first
            #     # editors = ["gedit", "kate", "code", "sublime_text"]
            #     editors = ["gedit", "kate", "sublime_text"]
            #     for editor in editors:
            #         try:
            #             subprocess.Popen([editor, file_path])
            #             return True
            #         except:
            #             continue
            #     # Fallback to terminal editors
            #     subprocess.Popen(["nano", file_path])

            # return True

            else:  # Linux / macOS
                try:
                    # Universal: open with system default editor
                    subprocess.Popen(["xdg-open", file_path])
                    return True
                except Exception:
                    # If xdg-open fails, try known GUI editors
                    editors = ["gedit", "kate", "sublime_text", "code"]
                    for editor in editors:
                        try:
                            subprocess.Popen([editor, file_path])
                            return True
                        except FileNotFoundError:
                            continue
                    # Last fallback: nano (only works if launched from a terminal)
                    try:
                        subprocess.Popen(
                            ["x-terminal-emulator", "-e", "nano", file_path]
                        )
                        return True
                    except Exception as e:
                        print(f"Failed to open file: {e}")
                        return False

        except Exception as e:
            # messagebox.showerror("Error", f"Failed to open file {file_path}: {e}")
            self.custom_msg_box.custom_showerror(
                self.root,
                "Error",
                f"Failed to open file {file_path}: {e}",
                self.messagebox_font,
            )

    # def open_download_folder(self):
    def open_folder(self, folder_name):
        """Platform-specific safe folder opening"""
        folder_path = self.settings.get(folder_name)
        try:
            if os.name == "nt":  # Windows
                subprocess.Popen(["explorer", folder_path])
            elif sys.platform == "darwin":  # macOS
                subprocess.Popen(["open", folder_path])
            else:  # Linux/WSL
                # Check if we're in WSL
                try:
                    with open("/proc/version", "r") as f:
                        if "microsoft" in f.read().lower():
                            # We're in WSL - use Windows Explorer
                            # Convert WSL path to Windows path
                            windows_path = subprocess.check_output(
                                ["wslpath", "-w", folder_path], text=True
                            ).strip()
                            subprocess.Popen(["explorer.exe", windows_path])
                            return True
                except Exception:
                    pass

                # Regular Linux - try GUI file managers
                file_managers = ["nautilus", "dolphin", "thunar", "pcmanfm"]
                for fm in file_managers:
                    try:
                        subprocess.Popen([fm, folder_path])
                        return True
                    except Exception:
                        continue

                # Fallback: just print the path
                print(f"Please navigate to: {folder_path}")

            return True
        except Exception as e:
            # messagebox.showerror("Error", f"Failed to open folder {folder_path}: {e}")
            self.custom_msg_box.custom_showerror(
                self.root,
                "Error",
                f"Failed to open folder {folder_path}: {e}",
                self.messagebox_font,
            )

    def play_latest_video(self):
        """Play the most recently downloaded video"""

        audio_video_extensions = {
            ".mp4",
            ".mkv",
            ".webm",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".m4v",
            ".3gp",
            ".gif",
            ".webp",
            ".m4a",
            ".mp3",
            ".aac",
            ".opus",
        }


        if self.download_context.download_path:
            if self.download_context.final_filename_check:
                file_ext = str(self.download_context.final_filename_check).rsplit(".", 1)[-1]
                file_ext = "." + file_ext
                if file_ext in audio_video_extensions:
                    final_filename_check = os.path.join(self.download_context.download_path, self.download_context.final_filename_check)
                    if os.path.exists(final_filename_check):
                        self.play_video(final_filename_check)
                        return

        latest_file = self.get_latest_downloaded_media(self.settings.get("downloads_dir"))
        if latest_file:
            self.play_video(latest_file)
            return
        else:
            # messagebox.showinfo("Info", "No video files found to play")
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No media files found to play",
                self.messagebox_font,
            )

    def play_video(self, video_path):
        if video_path and os.path.exists(video_path):
            try:
                if IS_WINDOWS:
                    os.startfile(video_path)
                elif IS_MAC:
                    subprocess.run(["open", video_path])
                elif IS_LINUX:
                    # Check if we're in WSL
                    try:
                        with open("/proc/version", "r") as f:
                            if "microsoft" in f.read().lower():
                                # We're in WSL - use Windows default player
                                windows_path = subprocess.check_output(
                                    ["wslpath", "-w", video_path], text=True
                                ).strip()
                                # Use Windows default program association
                                subprocess.run(
                                    ["cmd.exe", "/c", "start", '""', windows_path]
                                )
                                return
                    except Exception:
                        pass

                    # Try system default first, then fallbacks
                    players = ["xdg-open", "vlc", "mpv", "totem", "firefox", "chromium"]
                    for player in players:
                        try:
                            subprocess.run([player, video_path], check=True)
                            break
                        except FileNotFoundError:
                            continue
                    else:
                        raise Exception(
                            "No video player found. Please install VLC or another media player."
                        )

            except Exception as e:
                messagebox.showerror("Error", f"Could not play video: {e}")
        else:
            # messagebox.showinfo("Info", "No video files found to play")
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "No media files found to play",
                self.messagebox_font,
            )

    def get_latest_downloaded_media(
        self, download_dir: str, search_subfolders: bool = True
    ) -> Optional[str]:
        """Get the most recently downloaded complete video file"""
        try:
            if not os.path.exists(download_dir):
                return None

            video_extensions = {
                ".mp4",
                ".mkv",
                ".webm",
                ".avi",
                ".mov",
                ".wmv",
                ".flv",
                ".m4v",
                ".3gp",
                ".gif",
                ".webp",
                ".m4a",
                ".mp3",
                ".aac",
                ".opus",
            }
            video_files = []

            # Use recursive glob if subfolder search is enabled
            if search_subfolders:
                search_pattern = "**/*"  # Recursive search
            else:
                search_pattern = "*"  # Only current directory

            for file in Path(download_dir).glob(search_pattern):
                if file.is_file():  # Ensure it's a file, not a directory
                    file_suffix = file.suffix.lower()
                    if (
                        file_suffix in video_extensions
                        and file.stat().st_size > 102400  # >100KB
                        and not self.is_partial_download(file)
                    ):  # Exclude partial downloads
                        video_files.append(file)

            if not video_files:
                return None

            # Sort by modification time (newest first)
            video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return str(video_files[0])

        except Exception as e:
            print(f"Error finding latest video: {e}")
            return None

    def is_partial_download(self, file_path: Path) -> bool:
        """Check if file is a partial download"""
        partial_indicators = [".part", ".ytdl", ".temp", ".tmp", ".download"]
        return any(file_path.name.endswith(ext) for ext in partial_indicators)

    # def update_tools(self):
    def update_tools(self, update_button_clicked=False):
        """Update yt-dlp and FFmpeg"""
        if self.download_context.is_downloading:
            self.custom_msg_box.custom_showinfo(
                self.root,
                "Info",
                "Cannot update while a download is in progress",
                self.messagebox_font,
            )
            return
        else:
            threading.Thread(
                target=self._run_update_logic, args=(update_button_clicked,), daemon=True
            ).start()

    def _run_update_logic(self, update_button_clicked):
        """Wrapper to run do_update in a separate thread."""
        self.do_update(update_button_clicked)

    def _perform_startup_checks(self):
        """Perform checks for necessary tools and updates on startup."""
        # Store flag to track if initial tool download is needed
        self.initial_tools_downloading = (
            not self.ytdlp_tool.is_ytdlp_downloaded()
            or not self.spotdl_tool.is_spotdl_downloaded()
            or not self.deno_tool.is_deno_downloaded()
            or not self.ffmpeg_status["is_ffmpeg_suite_available"]
        )
        
        if self.initial_tools_downloading:
            # self.do_update()
            self.root.after(500, lambda: self.do_update())

    def should_check_app_update(self):
        """Check app updates once per week using date format"""
        import datetime

        # Get last check date (default to 0 if never checked)
        last_check_date = self.settings.get("last_app_update_check", 0)
        current_date = int(datetime.datetime.now().strftime("%Y%m%d"))

        try:
            # Check if 7 days have passed
            if current_date - last_check_date >= self.settings.app_update_frequency:
                self.settings.set("last_app_update_check", current_date)
                self.settings.save_settings()
                return True
        except:
            self.settings.set("last_app_update_check", current_date)
            self.settings.save_settings()
            return True
        return False

    def should_check_ytdlp_spotdl_updates(self):
        """Check ytdlp and spotdl updates once per week"""
        import datetime

        last_check_date = self.settings.get("last_tool_update_check", 0)
        current_date = int(datetime.datetime.now().strftime("%Y%m%d"))

        try:
            # Check if 7 days have passed
            if current_date - last_check_date >= self.settings.ytdlp_spotdl_update_frequency:
                self.settings.set("last_tool_update_check", current_date)
                self.settings.save_settings()
                return True
        except:
            self.settings.set("last_tool_update_check", current_date)
            self.settings.save_settings()
            return True
        return False

    def should_check_deno_update(self):
        """Check deno updates once every 60 days (2 months)"""
        import datetime

        last_check_date = self.settings.get("last_deno_update_check", 0)
        current_date = int(datetime.datetime.now().strftime("%Y%m%d"))

        try:
            # Check if 60 days have passed
            if current_date - last_check_date >= self.settings.deno_update_frequency:
                self.settings.set("last_deno_update_check", current_date)
                self.settings.save_settings()
                return True
        except:
            self.settings.set("last_deno_update_check", current_date)
            self.settings.save_settings()
            return True
        return False

    def do_update(self, update_button_clicked=False):
        """Perform tool updates"""
        if hasattr(self, 'is_updating') and self.is_updating:
            return  # Already updating, do nothing

        self.is_updating = True
        self.update_status(
            f"{self.style_manager.get_emoji('loading')} Wait...Checking tools status"
        )
        self.root.update()

        # ytdlp_missing = not self.ytdlp_status["is_ytdlp_downloaded"]
        # spotdl_missing = not self.spotdl_status["is_spotdl_downloaded"]
        # deno_missing = not self.deno_tool.is_deno_downloaded()
        ytdlp_missing = not self.ytdlp_tool.is_ytdlp_downloaded()
        spotdl_missing = not self.spotdl_tool.is_spotdl_downloaded()
        deno_missing = not self.deno_tool.is_deno_downloaded()

        missing_tools = []
        if ytdlp_missing:
            missing_tools.append("yt-dlp")
        if spotdl_missing:
            missing_tools.append("spotdl")
        if deno_missing:
            missing_tools.append("deno")

        if missing_tools:
            tool_str = " and ".join(missing_tools)
            self.update_status(
                f"{self.style_manager.get_emoji('error')} {tool_str} Missing.",
                error=True,
            )
            if self.custom_msg_box.custom_askyesno(
                self.root,
                f"{tool_str} Missing",
                f"{tool_str} required for the app to work.\n\nWould you like to download {tool_str} now?",
                self.messagebox_font,
            ):
                self.do_update_tools(ytdlp_missing, spotdl_missing, deno_missing)
            else:
                self.update_status(
                    f"{tool_str} required, update to download",
                    error=True,
                )
                self.root.update()
                # User declined, mark initial download as complete and proceed to session check
                self.initial_tools_downloading = False
                self._finalize_startup()
        else:
            # All tools exist, now check for version updates
            should_check_tools = update_button_clicked or self.should_check_ytdlp_spotdl_updates()
            should_check_deno = update_button_clicked or self.should_check_deno_update()
            
            updates_needed = []
            
            # Check ytdlp version
            if should_check_tools:
                try:
                    self.current_version_ytdlp = self.ytdlp_tool.get_ytdlp_current_version()
                    self.latest_version_ytdlp = self.ytdlp_tool.get_ytdlp_latest_version()
                    
                    if self.current_version_ytdlp and self.latest_version_ytdlp:
                        if self.current_version_ytdlp != self.latest_version_ytdlp:
                            updates_needed.append(("yt-dlp", self.current_version_ytdlp, self.latest_version_ytdlp))
                        else:
                            self.update_status(f"yt-dlp v{self.current_version_ytdlp} is up to date")
                    else:
                        print("Could not determine yt-dlp versions")
                except Exception as e:
                    print(f"yt-dlp version check failed: {e}")
            
            # Check spotdl version
            if should_check_tools:
                try:
                    current_spotdl_version = self.spotdl_tool.get_spotdl_current_version()
                    latest_spotdl_version = self.spotdl_tool.get_spotdl_latest_version()
                    
                    if current_spotdl_version and latest_spotdl_version:
                        if current_spotdl_version != latest_spotdl_version:
                            updates_needed.append(("spotdl", current_spotdl_version, latest_spotdl_version))
                        else:
                            self.update_status(f"spotdl v{current_spotdl_version} is up to date")
                    else:
                        print("Could not determine spotdl versions")
                except Exception as e:
                    print(f"spotdl version check failed: {e}")
            
            # Check deno version
            if should_check_deno:
                try:
                    current_deno_version = self.deno_tool.get_deno_current_version()
                    latest_deno_version = self.deno_tool.get_deno_latest_version()
                    if current_deno_version and latest_deno_version:
                        if current_deno_version != latest_deno_version:
                            updates_needed.append(("deno", current_deno_version, latest_deno_version))
                        else:
                            self.update_status(f"deno v{current_deno_version} is up to date")
                    else:
                        print("Could not determine deno versions")
                except Exception as e:
                    print(f"deno version check failed: {e}")
            
            # Prompt for updates if needed
            if updates_needed:
                update_messages = []
                for tool, current, latest in updates_needed:
                    update_messages.append(f"{tool}: {current} → {latest}")
                
                message = "Updates available:\n\n" + "\n".join(update_messages) + "\n\nProceed with updates?"
                
                if self.custom_msg_box.custom_askyesno(
                    self.root,
                    "Tool Updates Available",
                    message,
                    self.messagebox_font,
                ):
                    # Determine which tools need updating
                    needs_ytdlp = any(t[0] == "yt-dlp" for t in updates_needed)
                    needs_spotdl = any(t[0] == "spotdl" for t in updates_needed)
                    needs_deno = any(t[0] == "deno" for t in updates_needed)
                    self.do_update_tools(needs_ytdlp, needs_spotdl, needs_deno)
                else:
                    self.check_dependencies()
            else:
                # No updates needed, check dependencies
                self.check_dependencies()
            
            # Show info message if manually triggered and all up to date
            if update_button_clicked and not updates_needed:
                tools_status = []
                if should_check_tools and self.current_version_ytdlp:
                    tools_status.append(f"yt-dlp v{self.current_version_ytdlp}")
                if should_check_tools:
                    spotdl_ver = self.spotdl_tool.get_spotdl_current_version()
                    if spotdl_ver:
                        tools_status.append(f"spotdl v{spotdl_ver}")
                if should_check_deno:
                    deno_ver = self.deno_tool.get_deno_current_version()
                    if deno_ver:
                        tools_status.append(f"deno v{deno_ver}")
                
                self.custom_msg_box.custom_showinfo(
                    self.root,
                    "Update Check",
                    "All tools are up to date!\n\n" + "\n".join(tools_status) if tools_status else "All tools are up to date!",
                    self.messagebox_font,
                )

        self.update_status("")
        
        # Check app update (weekly)
        should_check_app = update_button_clicked or self.should_check_app_update()        
        if should_check_app:
            self.check_app_update()
    def check_app_update(self):
        """Check for new version from GitHub version.txt"""
        try:
            if not self.root or not self.root.winfo_exists():
                return

            import requests

            response = requests.get(VERSION_URL, timeout=10)
            if response.status_code == 200:
                latest_version = response.text.strip()

                # Simple version comparison
                current_parts = [int(x) for x in __version__.split(".")]
                latest_parts = [int(x) for x in latest_version.split(".")]

                # Pad with zeros for equal length
                max_len = max(len(current_parts), len(latest_parts))
                current_parts += [0] * (max_len - len(current_parts))
                latest_parts += [0] * (max_len - len(latest_parts))

                if latest_parts > current_parts:
                    self._show_update_notification(latest_version)

        except Exception as e:
            print(f"App update check failed: {e}")

    def check_dependencies(self):
        # Check FFmpeg
        self.update_status(
            f"{self.style_manager.get_emoji('loading')} Wait...Checking FFmpeg status",
            percent=0,
        )
        # FFmpeg missing
        if not self.ffmpeg_status["is_ffmpeg_suite_available"]:
            self.update_status(
                f"{self.style_manager.get_emoji('error')} FFmpeg Missing",
                error=True,
            )
            if self.custom_msg_box.custom_askyesno(
                self.root,
                "FFmpeg Missing",
                "FFmpeg is required for video and audio processing features.\n\n• Click 'Yes' to download FFmpeg automatically\n• Click 'No' to skip or install manually",
                self.messagebox_font,
            ):
                self.ffmpeg_update_running = True
                self.do_update_ffmpeg()
            else:
                self.update_status(
                    "FFmpeg Missing. Settings option set: Video Format - b"
                )
                self.settings.set("stream_and_merge_format", "b")
                self.settings.save_settings()
                # Proceed to session check even if FFmpeg declined
                self._finalize_startup()

        # FFmpeg found on system, but not downloaded by video downloader
        elif (
            not self.ffmpeg_status["is_ffmpeg_suite_downloaded"]
            and self.ffmpeg_status["is_ffmpeg_suite_installed"]
        ):
            version_info = self.get_ffmpeg_version()
            if version_info:
                version_type, version_data, build_date = version_info
                if not self.is_ffmpeg_version_recent(version_info):
                    if self.custom_msg_box.custom_askyesno(
                        self.root,
                        "FFmpeg Update",
                        f"Your FFmpeg version {version_data} may be outdated.\n\n"
                        "Download a newer version?",
                        self.messagebox_font,
                    ):
                        self.ffmpeg_update_running = True
                        self.gui_context.buttons["download_btn"].config(
                            state="disabled"
                        )
                        self.gui_context.buttons["audio_download_btn"].config(
                            state="disabled"
                        )
                        self.do_update_ffmpeg()
                    else:
                        self.update_status(
                            "FFmpeg not updated, with outdated FFmpeg, video downloader may not work as expected",
                            percent=0,
                        )
                        self._finalize_startup()
                else:
                    # self.update_status(
                    #     f"FFmpeg version {version_data} is compatible with video downloader {self.style_manager.get_emoji('check')}",
                    #     percent=0,
                    # )
                    self.update_status(
                        f"{self.style_manager.get_emoji('check')} Ready to download Video/Audio",
                        percent=0,
                    )
                    self._finalize_startup()
            else:
                self.update_status(
                    "Could not determine FFmpeg version, video downloader may not work as expected",
                    percent=0,
                )
                self._finalize_startup()
        elif self.ffmpeg_status["is_ffmpeg_suite_downloaded"]:
            self.update_status(
                f"{self.style_manager.get_emoji('check')} Ready to download Video/Audio",
                percent=0,
            )
            self._finalize_startup()                        
        else:
            self.update_status("", percent=0)
            self._finalize_startup()

    def _finalize_startup(self):
        """Call this only after ALL tools are ready"""
        # Prevent multiple calls to check_previous_session
        if not self.session_check_completed:
            self.session_check_completed = True
            self.initial_tools_downloading = False
            self.is_updating = False
            self.q_manager.check_previous_session(self.root)

    def do_update_tools(self, ytdlp_missing, spotdl_missing, deno_missing):
        """Download and update all required tools in sequence."""
        
        tools_to_download = []
        if ytdlp_missing: tools_to_download.append("yt-dlp")
        if spotdl_missing: tools_to_download.append("spotdl")
        if deno_missing: tools_to_download.append("deno")

        def final_callback(success, error=None):
            if success:
                tool_str = " and ".join(tools_to_download)
                self.custom_msg_box.custom_showinfo(
                    self.root,
                    "Downloads Complete",
                    f"Successfully downloaded: {tool_str}",
                    self.messagebox_font,
                )
            # After all tools are updated, check dependencies (FFmpeg)
            self.check_dependencies()

        def deno_callback(success, error=None):
            if success:
                final_callback(True)
            else:
                final_callback(False, "Deno download failed")

        def spotdl_callback(success, error=None):
            if success:
                if deno_missing:
                    self.do_update_deno(deno_callback, show_success_message=False)
                else:
                    final_callback(True)
            else:
                final_callback(False, "Spotdl download failed")

        def ytdlp_callback(success, error=None):
            if success:
                if spotdl_missing:
                    self.do_update_spotdl(spotdl_callback, show_success_message=False)
                elif deno_missing:
                    self.do_update_deno(deno_callback, show_success_message=False)
                else:
                    final_callback(True)
            else:
                final_callback(False, "Ytdlp download failed")

        if ytdlp_missing:
            self.do_update_yt_dlp(ytdlp_callback, show_success_message=False)
        elif spotdl_missing:
            self.do_update_spotdl(spotdl_callback, show_success_message=False)
        elif deno_missing:
            self.do_update_deno(deno_callback, show_success_message=False)
        else:
            self.check_dependencies()

    def _ffmpeg_update_success(self):
        """Called when FFmpeg update completes successfully"""
        # Update status and progress
        self.update_status(
            f"{self.style_manager.get_emoji('check')} FFmpeg downloaded/updated successfully! {self.style_manager.get_emoji('check')} Ready to download Video/Audio",
            percent=0,
        )

        # Refresh FFmpeg status
        self.download_context.ffmpeg_status = self.ffmpeg_tool.get_ffmpeg_status()

        # Re-enable button
        self.gui_context.buttons["update_btn"].config(state="normal")
        self.gui_context.buttons["download_btn"].config(state="normal")
        self.gui_context.buttons["audio_download_btn"].config(state="normal")

        self.ffmpeg_update_running = False

        self.root.update()

        # NOW it's safe to check previous session
        self._finalize_startup()

    def _ffmpeg_update_failed(self, error_message):
        """Called when FFmpeg update fails"""
        # Show error
        self.update_status(
            f"{self.style_manager.get_emoji('error')} FFmpeg update failed",
            error=True,
            percent=0,
        )

        # Show error message box
        self.custom_msg_box.custom_showerror(
            self.root,
            "FFmpeg Error",
            f"Failed to update FFmpeg:\n{error_message}",
            self.messagebox_font,
        )

        # Re-enable button
        self.gui_context.buttons["update_btn"].config(state="normal")
        self.gui_context.buttons["download_btn"].config(state="normal")
        self.gui_context.buttons["audio_download_btn"].config(state="normal")

        self.ffmpeg_update_running = False
        
        # Even if FFmpeg failed, proceed to session check
        self._finalize_startup()

    def startup_functions(self):
        """Startup functions"""
        if self.settings.get("auto_update"):
            self.root.after(1000, self.do_update_then_continue)
        else:
            # If no auto-update AND no initial tools downloading, go to session check
            if not self.initial_tools_downloading:
                self._finalize_startup()

    def do_update_then_continue(self):
        """Do update then continue with startup"""
        try:
            if self.should_check_app_update() or \
                self.should_check_ytdlp_spotdl_updates() or \
                self.should_check_deno_update():
                self.do_update()  # Your existing update function
        finally:
            # Only continue if tools were already present at startup
            if os.path.exists(self.ytdlp_path) and not self.ffmpeg_update_running and not self.initial_tools_downloading:
                self._finalize_startup()


    def _show_update_notification(self, new_version):
        """Show update notification"""
        message = f"Get new version v{new_version} with:\nBug fixes/ Improved performance/ New features/ Enhancements\nWould you like to visit the download page?"

        if self.custom_msg_box.custom_askyesno(
            self.root,
            f"Update Available - MediaTools Video Downloader, New version v{new_version}!",
            message,
            self.messagebox_font,
        ):
            import webbrowser

            webbrowser.open(DOWNLOAD_PAGE)

    def do_update_spotdl(self, callback=None, show_success_message=True):
        """Perform the actual download and replacement of spotdl."""
        self.gui_context.buttons["update_btn"].config(state="disabled")
        self.gui_context.buttons["download_btn"].config(state="disabled")
        self.gui_context.buttons["audio_download_btn"].config(state="disabled")

        def spotdl_thread():
            try:
                if os.path.exists(self.spotdl_path):
                    # Backup old version
                    backup_path = self.get_backup_filename(self.spotdl_path)
                    os.rename(self.spotdl_path, backup_path)
                    print(f"Backed up old version to {backup_path}")

                url = self.spotdl_tool.get_spotdl_latest_url()
                print(f"Downloading spotdl from {url}")
                if not url:
                    raise Exception("Could not get the download URL for spotdl")

                self.root.after(
                    0,
                    lambda: self.update_status(
                        f"{self.style_manager.get_emoji('loading')} Downloading spotdl..."
                    ),
                )

                # Use requests for better progress tracking
                response = requests.get(url, stream=True)
                total_size = int(response.headers.get("content-length", 0))
                print(f"Total size to download: {total_size} bytes")
                downloaded = 0
                with open(self.spotdl_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Update progress in main thread (capture values)
                            if total_size > 0:
                                current_percent = (downloaded / total_size) * 100
                                current_downloaded = downloaded
                                current_total = total_size

                                status_text = (
                                    f"{self.style_manager.get_emoji('loading')} "
                                    f"Downloading spotdl: {current_percent:.1f}% "
                                    f"({current_downloaded//1024}KB/{current_total//1024}KB)"
                                )

                                self.update_status(
                                    status_text,
                                    percent=current_percent,
                                )

                # Make executable on Unix-like systems
                if IS_LINUX or IS_MAC:
                    os.chmod(self.spotdl_path, 0o755)



                # Update status for extraction
                self.root.after(
                    0,
                    lambda: self.update_status(
                        f"{self.style_manager.get_emoji('check')} spotdl download complete",
                        percent=100,
                    ),
                )
                if show_success_message:
                    self.custom_msg_box.custom_showinfo(
                        self.root,
                        "Update Success",
                        f"Downloaded/Updated spotdl",
                        self.messagebox_font,
                    )

                self.gui_context.buttons["update_btn"].config(state="normal")
                self.gui_context.buttons["download_btn"].config(state="normal")
                self.gui_context.buttons["audio_download_btn"].config(state="normal")

                if callback:
                    callback(True)

            except Exception as e:

                # Show error
                self.update_status(
                    f"{self.style_manager.get_emoji('error')} spotdl update failed",
                    error=True,
                    percent=0,
                )

                self.custom_msg_box.custom_showerror(
                    self.root,
                    "Download Failed",
                    f"Could not download/update:\n{str(e)}",
                    self.messagebox_font,
                )

                # Restore backup if update failed
                if (
                    "backup_path" in locals()
                    and os.path.exists(backup_path)
                    and not os.path.exists(self.spotdl_path)
                ):
                    os.rename(backup_path, self.spotdl_path)
                    self.custom_msg_box.custom_showinfo(
                        self.root,
                        "Restored",
                        "Old version restored.",
                        self.messagebox_font,
                    )

                self.gui_context.buttons["update_btn"].config(state="normal")
                self.gui_context.buttons["download_btn"].config(state="normal")
                self.gui_context.buttons["audio_download_btn"].config(state="normal")

                if callback:
                    callback(False)

        threading.Thread(target=spotdl_thread, daemon=True).start()

    def do_update_deno(self, callback=None, show_success_message=True):
        """Perform the actual download and replacement of deno."""
        self.gui_context.buttons["update_btn"].config(state="disabled")
        self.gui_context.buttons["download_btn"].config(state="disabled")
        self.gui_context.buttons["audio_download_btn"].config(state="disabled")

        def deno_thread():
            try:
                # url = self.deno_status["deno_latest_url"]
                url = self.deno_tool.get_deno_latest_url()
                if not url:
                    raise Exception("Could not get the download URL for deno")

                self.root.after(
                    0,
                    lambda: self.update_status(
                        f"{self.style_manager.get_emoji('loading')} Downloading deno..."
                    ),
                )

                archive_path = os.path.join(self.bin_dir, "deno_download.tmp")
                
                response = requests.get(url, stream=True)
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                with open(archive_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                current_percent = (downloaded / total_size) * 100
                                status_text = (
                                    f"{self.style_manager.get_emoji('loading')} "
                                    f"Downloading deno: {current_percent:.1f}%"
                                )
                                self.update_status(status_text, percent=current_percent)
                
                self.root.after(
                    0,
                    lambda: self.update_status(
                        f"deno download complete. Extracting...",
                        percent=100,
                    ),
                )

                import zipfile
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    for file in zip_ref.namelist():
                        if file.endswith(self.deno_tool.LOCAL_FILENAMES_DENO[self.deno_tool.current_platform]):
                            zip_ref.extract(file, self.bin_dir)
                            extracted_path = os.path.join(self.bin_dir, file)
                            os.rename(extracted_path, self.deno_path)
                            break
                
                if IS_LINUX or IS_MAC:
                    os.chmod(self.deno_path, 0o755)

                os.remove(archive_path)

                self.root.after(
                    0,
                    lambda: self.update_status(
                        f"{self.style_manager.get_emoji('check')} deno download complete",
                        percent=100,
                    ),
                )
                if show_success_message:
                    self.custom_msg_box.custom_showinfo(
                        self.root,
                        "Update Success",
                        f"Downloaded/Updated deno",
                        self.messagebox_font,
                    )

                self.gui_context.buttons["update_btn"].config(state="normal")
                self.gui_context.buttons["download_btn"].config(state="normal")
                self.gui_context.buttons["audio_download_btn"].config(state="normal")

                if callback:
                    callback(True)

            except Exception as e:
                self.update_status(
                    f"{self.style_manager.get_emoji('error')} deno update failed",
                    error=True,
                    percent=0,
                )
                self.custom_msg_box.custom_showerror(
                    self.root,
                    "Download Failed",
                    f"Could not download/update deno:\n{str(e)}",
                    self.messagebox_font,
                )
                self.gui_context.buttons["update_btn"].config(state="normal")
                self.gui_context.buttons["download_btn"].config(state="normal")
                self.gui_context.buttons["audio_download_btn"].config(state="normal")
                if callback:
                    callback(False, str(e))
        
        threading.Thread(target=deno_thread, daemon=True).start()

    def get_ffmpeg_version(self):
        """Get FFmpeg version, handling both stable and development builds"""
        try:
            process_kwargs = {
                "capture_output": True,
                "text": True,
                "timeout": 10,
            }
            if IS_WINDOWS:
                process_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                ["ffmpeg", "-version"],
                **process_kwargs
            )
            if result.returncode == 0:
                # Fixed regex - case insensitive, captures version part only
                match = re.search(
                    r"ffmpeg\s+version\s+([^\s]+)", result.stdout, re.IGNORECASE
                )
                if match:
                    version_str = match.group(1)  # "8.0-full_build-www.gyan.dev"
                    return self.parse_ffmpeg_version(version_str)
            return None
        except Exception:
            return None

    def do_update_ffmpeg(self):
        """Start FFmpeg download and extraction in separate thread"""
        self.ffmpeg_update_running = True
        # Disable update button to prevent multiple clicks
        self.gui_context.buttons["update_btn"].config(state="disabled")
        self.gui_context.buttons["download_btn"].config(state="disabled")
        self.gui_context.buttons["audio_download_btn"].config(state="disabled")

        # Show initial status
        self.update_status(
            f"{self.style_manager.get_emoji('loading')} Starting FFmpeg update...",
            percent=0,
        )
        self.root.update()

        # Start the process in a background thread
        self.ffmpeg_thread = threading.Thread(
            target=self._download_and_extract_ffmpeg_threaded,
            daemon=True,  # Thread will exit when main program exits
        )
        self.ffmpeg_thread.start()

    def _download_and_extract_ffmpeg_threaded(self):
        """Run download and extraction in background thread"""
        try:
            self._download_ffmpeg_with_progress()
            self._extract_ffmpeg()
            self.root.after(0, self._ffmpeg_update_success)

        except Exception as e:
            # Capture error message immediately to avoid scope issues
            error_message = str(e)
            print(f"FFmpeg update error in thread: {error_message}")
            self.root.after(0, lambda: self._ffmpeg_update_failed(error_message))

    def _download_ffmpeg_with_progress(self):
        """Download FFmpeg with progress tracking"""
        url = self.ffmpeg_status["ffmpeg_latest_url"]

        archive_path = os.path.join(self.bin_dir, "ffmpeg_download.tmp")

        # Update status in main thread
        self.root.after(
            0,
            lambda: self.update_status(
                f"{self.style_manager.get_emoji('loading')} Downloading FFmpeg..."
            ),
        )

        response = requests.get(url, stream=True)
        total_size = int(response.headers.get("content-length", 0))

        downloaded = 0
        with open(archive_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Update progress in main thread (capture values)
                    if total_size > 0:
                        current_percent = (downloaded / total_size) * 100
                        current_downloaded = downloaded
                        current_total = total_size

                        status_text = (
                            f"{self.style_manager.get_emoji('loading')} "
                            f"Downloading FFmpeg: {current_percent:.1f}% "
                            f"({current_downloaded//1024}KB/{current_total//1024}KB)"
                        )

                        self.update_status(
                            status_text,
                            percent=current_percent,
                        )

    def _extract_ffmpeg(self):
        """Extract FFmpeg files"""
        local_filenames_ffmpeg = self.ffmpeg_tool.LOCAL_FILENAMES_FFMPEG
        local_filenames_ffprobe = self.ffmpeg_tool.LOCAL_FILENAMES_FFPROBE
        ffmpeg_path = self.ffmpeg_status["ffmpeg_path"]
        ffprobe_path = self.ffmpeg_status["ffprobe_path"]

        archive_path = os.path.join(self.bin_dir, "ffmpeg_download.tmp")

        # Update status for extraction
        self.root.after(
            0,
            lambda: self.update_status(
                f"FFmpeg download complete. Extracting...",
                percent=100,
            ),
        )

        # Extract both FFmpeg and ffprobe depending on platform
        if IS_WINDOWS:
            import zipfile

            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith(local_filenames_ffmpeg["Windows"]):
                        zip_ref.extract(file, self.bin_dir)
                        extracted_path = os.path.join(self.bin_dir, file)
                        os.rename(extracted_path, ffmpeg_path)
                    elif file.endswith(local_filenames_ffprobe["Windows"]):
                        zip_ref.extract(file, self.bin_dir)
                        extracted_path = os.path.join(self.bin_dir, file)
                        os.rename(extracted_path, ffprobe_path)

        elif IS_MAC:
            import zipfile

            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith(local_filenames_ffmpeg["Darwin"]):
                        zip_ref.extract(file, self.bin_dir)
                        extracted_path = os.path.join(self.bin_dir, file)
                        os.rename(extracted_path, ffmpeg_path)
                    elif file.endswith(local_filenames_ffprobe["Darwin"]):
                        zip_ref.extract(file, self.bin_dir)
                        extracted_path = os.path.join(self.bin_dir, file)
                        os.rename(extracted_path, ffprobe_path)
                        os.chmod(ffprobe_path, 0o755)

        elif IS_LINUX:
            import tarfile

            with tarfile.open(archive_path, "r:xz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith("/" + local_filenames_ffmpeg["Linux"]):
                        tar.extract(member, self.bin_dir)
                        extracted_path = os.path.join(self.bin_dir, member.name)
                        os.rename(extracted_path, ffmpeg_path)
                        os.chmod(ffmpeg_path, 0o755)
                    elif member.name.endswith("/" + local_filenames_ffprobe["Linux"]):
                        tar.extract(member, self.bin_dir)
                        extracted_path = os.path.join(self.bin_dir, member.name)
                        os.rename(extracted_path, ffprobe_path)
                        os.chmod(ffprobe_path, 0o755)

        # Make executables
        if not IS_WINDOWS:
            os.chmod(ffmpeg_path, 0o755)
            if os.path.exists(ffprobe_path):
                os.chmod(ffprobe_path, 0o755)

        os.remove(archive_path)

    # def _ffmpeg_update_success(self):
    #     """Called when FFmpeg update completes successfully"""
    #     # Update status and progress
    #     self.update_status(
    #         f"{self.style_manager.get_emoji('check')} FFmpeg downloaded/updated successfully!",
    #         percent=0,
    #     )

    #     # Refresh FFmpeg status
    #     self.download_context.ffmpeg_status = self.ffmpeg_tool.get_ffmpeg_status()

    #     # Re-enable button
    #     self.gui_context.buttons["update_btn"].config(state="normal")
    #     self.gui_context.buttons["download_btn"].config(state="normal")
    #     self.gui_context.buttons["audio_download_btn"].config(state="normal")

    #     self.ffmpeg_update_running = False

    #     self.root.update()

    #     self.q_manager.check_previous_session(self.root)

    # def _ffmpeg_update_failed(self, error_message):
    #     """Called when FFmpeg update fails"""
    #     # Show error
    #     self.update_status(
    #         f"{self.style_manager.get_emoji('error')} FFmpeg update failed",
    #         error=True,
    #         percent=0,
    #     )

    #     # Show error message box
    #     self.custom_msg_box.custom_showerror(
    #         self.root,
    #         "FFmpeg Error",
    #         f"Failed to update FFmpeg:\n{error_message}",
    #         self.messagebox_font,
    #     )

    #     # Re-enable button
    #     self.gui_context.buttons["update_btn"].config(state="normal")
    #     self.gui_context.buttons["download_btn"].config(state="normal")
    #     self.gui_context.buttons["audio_download_btn"].config(state="normal")

    #     self.ffmpeg_update_running = False

    def parse_ffmpeg_version(self, version_str):
        """
        Parse FFmpeg version string into comparable format
        Returns: (version_type, version_data, build_date)
        """
        # Stable release pattern: "4.4.2" or "5.0.1"
        stable_match = re.match(r"(\d+\.\d+\.?\d*)", version_str)

        if stable_match:
            return ("stable", stable_match.group(1), None)

        # Development build pattern: "N-118595-gdede00f003-20250302"
        dev_match = re.match(r"N-(\d+)-g([a-f0-9]+)-(\d+)", version_str)

        if dev_match:
            commit_number = int(dev_match.group(1))
            build_date = dev_match.group(3)  # YYYYMMDD
            return ("development", commit_number, build_date)

        # Unknown format
        return ("unknown", version_str, None)

    def is_ffmpeg_version_recent(
        self, version_info, min_commit=100000, min_build_date="20240101"
    ):
        """
        Check if FFmpeg version is sufficiently recent
        version_info: tuple from parse_ffmpeg_version()
        """
        if not version_info:
            return False

        version_type, version_data, build_date = version_info

        if version_type == "stable":
            # Compare stable versions (e.g., 5.0 > 4.4)
            try:
                from packaging import version

                return version.parse(version_data) >= version.parse("5.0")
            except ImportError:
                # Fallback if packaging library not available
                version_parts = [int(x) for x in version_data.split(".")]
                return version_parts[0] >= 5

        elif version_type == "development":
            # Compare development builds by commit number and build date
            commit_number = version_data
            return commit_number >= min_commit and (
                not build_date or build_date >= min_build_date
            )

        return False  # Unknown version type

    def do_update_yt_dlp(self, callback=None, show_success_message=True):
        """Perform the actual download and replacement of yt-dlp."""
        self.gui_context.buttons["update_btn"].config(state="disabled")
        self.gui_context.buttons["download_btn"].config(state="disabled")
        self.gui_context.buttons["audio_download_btn"].config(state="disabled")

        def ytdlp_thread():
            try:
                if os.path.exists(self.ytdlp_path):
                    # Backup old version
                    backup_path = self.get_backup_filename(self.ytdlp_path)
                    os.rename(self.ytdlp_path, backup_path)
                    print(f"Backed up old version to {backup_path}")

                # url = self.ytdlp_status["ytdlp_latest_url"]
                url = self.ytdlp_tool.get_ytdlp_latest_url()
                self.root.after(
                    0,
                    lambda: self.update_status(
                        f"{self.style_manager.get_emoji('loading')} Downloading Yt-dlp..."
                    ),
                )

                # Use requests for better progress tracking
                response = requests.get(url, stream=True)
                total_size = int(response.headers.get("content-length", 0))

                downloaded = 0
                with open(self.ytdlp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Update progress in main thread (capture values)
                            if total_size > 0:
                                current_percent = (downloaded / total_size) * 100
                                current_downloaded = downloaded
                                current_total = total_size

                                status_text = (
                                    f"{self.style_manager.get_emoji('loading')} "
                                    f"Downloading Yt-dlp: {current_percent:.1f}% "
                                    f"({current_downloaded//1024}KB/{current_total//1024}KB)"
                                )

                                self.update_status(
                                    status_text,
                                    percent=current_percent,
                                )

                # Make executable on Unix-like systems
                if IS_LINUX or IS_MAC:
                    os.chmod(self.ytdlp_path, 0o755)

                version = subprocess.run(
                    [self.ytdlp_path, "--version"],
                    **self.kwargs,
                )
                if version.returncode == 0:
                    # Update status for extraction
                    self.root.after(
                        0,
                        lambda: self.update_status(
                            f"{self.style_manager.get_emoji('check')} Yt-dlp download complete",
                            percent=100,
                        ),
                    )
                    self.current_version_ytdlp = version.stdout.strip()
                    self.latest_version_ytdlp = self.current_version_ytdlp
                    if show_success_message:
                        self.custom_msg_box.custom_showinfo(
                            self.root,
                            "Update Success",
                            f"Downloaded/Updated to yt-dlp v{version.stdout.strip()}",
                            self.messagebox_font,
                        )

                    self.gui_context.buttons["update_btn"].config(state="normal")
                    self.gui_context.buttons["download_btn"].config(state="normal")
                    self.gui_context.buttons["audio_download_btn"].config(state="normal")

                    if callback:
                        callback(True)
                else:
                    self.gui_context.buttons["update_btn"].config(state="normal")
                    self.gui_context.buttons["download_btn"].config(state="normal")
                    self.gui_context.buttons["audio_download_btn"].config(state="normal")

                    if callback:
                        callback(False, "Post-update version check failed")

                    raise Exception("Post-update version check failed")

            except Exception as e:

                # Show error
                self.update_status(
                    f"{self.style_manager.get_emoji('error')} Yt-dlp update failed",
                    error=True,
                    percent=0,
                )

                self.custom_msg_box.custom_showerror(
                    self.root,
                    "Download Failed",
                    f"Could not download/update:\n{str(e)}",
                    self.messagebox_font,
                )

                # Restore backup if update failed
                if (
                    "backup_path" in locals()
                    and os.path.exists(backup_path)
                    and not os.path.exists(self.ytdlp_path)
                ):
                    os.rename(backup_path, self.ytdlp_path)
                    self.custom_msg_box.custom_showinfo(
                        self.root,
                        "Restored",
                        "Old version restored.",
                        self.messagebox_font,
                    )

                self.gui_context.buttons["update_btn"].config(state="normal")
                self.gui_context.buttons["download_btn"].config(state="normal")
                self.gui_context.buttons["audio_download_btn"].config(state="normal")

                if callback:
                    callback(False, str(e))

        threading.Thread(target=ytdlp_thread, daemon=True).start()

    def get_backup_filename(self, original_path):
        """Generate a backup filename with timestamp before the extension."""
        base, ext = os.path.splitext(original_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base}_old_{timestamp}{ext}"

    def open_file(self, file_path):
        """Open a file with default application"""
        try:
            if IS_WINDOWS:
                os.startfile(str(file_path))
            elif IS_MAC:
                subprocess.run(["open", str(file_path)])
            elif IS_LINUX:
                subprocess.run(["xdg-open", str(file_path)])
        except Exception as e:
            # messagebox.showerror("Error", f"Could not open file: {e}")
            self.custom_msg_box.custom_showerror(
                self.root,
                "Error",
                f"Could not open file: {e}",
                self.messagebox_font,
            )

    def run(self):
        """Start the application"""
        self.startup_functions()

        # Start queue polling
        self.root.after(3000, self.start_queue_polling)

        # Start main loop
        self.root.mainloop()

    def start_queue_polling(self):
        """Start polling for queue items"""
        if (
            not self.download_context.is_downloading
            and self.q_manager.has_queued_urls()
            and self.q_manager.get_previous_session_check_done()
        ):
            self.start_queue_processing()

            # Update queue display
            self.update_queue_display(self.gui_context.status_label_fg)

        # Schedule next poll
        self.root.after(2000, self.start_queue_polling)

    def apply_theme(self):
        """Apply updated theme"""
        self.theme_manager.setup_styles()
        self.update_queue_display(self.gui_context.status_label_fg)

    def check_internet_connection(self):
        """Check internet connectivity"""
        # Test multiple reliable endpoints
        test_urls = [
            "https://www.google.com",
            "https://www.cloudflare.com",
            "https://1.1.1.1",
        ]

        for url in test_urls:
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "VideoDownloader/1.0"}
                )
                with urllib.request.urlopen(request, timeout=3) as response:
                    if response.getcode() == 200:
                        return True
            except:
                continue

        return False

    # def get_app_root(self):
    #     """Get the application root directory"""
    #     if hasattr(sys, "_MEIPASS"):
    #         # PyInstaller: use the temp extraction directory
    #         return Path(sys._MEIPASS)
    #     else:
    #         # Development: go up from current file location
    #         return Path(__file__).parent

    def get_app_root(self):
        """Get the application root directory"""
        # Make sure frozen check comes first
        if getattr(sys, "frozen", False):
            # PyInstaller build (onefile or onedir)
            exe_dir = Path(sys.executable).parent
            if (exe_dir / "_internal").exists():
                return Path(sys.executable).parent
            else:
                return Path(sys._MEIPASS)
        else:
            # Development
            return Path(__file__).parent

    def _setup_subprocess_kwargs(self):
        """Setup platform-specific subprocess arguments"""
        self.kwargs = {
            "capture_output": True,
            "text": True,
        }

        # Windows-specific: hide console window
        if IS_WINDOWS:
            self.kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    def add_to_delete_list(self, base_name, download_dir):
        """Delete files related to download that was stopped/t"""
        self.stopped_downloads_to_be_deleted.append(
            os.path.join(download_dir, base_name)
        )

    def exit_app(self):
        """Handle application shutdown"""
        try:
            self.cancel_all_background_tasks()
            self.download_context.is_paused = True
            status_text = f"{self.style_manager.get_emoji('loading')} Exiting....."
            self.update_status(status_text, 0, "")
            self.root.update()
            time.sleep(1)
            if self.download_context.current_process or self.download_context.stopdl_process:
                try:
                    if self.download_context.stopdl_process:
                        self.download_service.stop_download_core(self.download_context.stopdl_process)
                        time.sleep(2)
                    if self.download_context.current_process:
                        self.download_service.stop_download_core(self.download_context.current_process)
                    # if self.download_context.current_process.poll() is None:
                    #     self.download_context.current_process.terminate()
                    #     try:
                    #         self.download_context.current_process.wait(timeout=3)
                    #     except subprocess.TimeoutExpired:
                    #         self.download_context.current_process.kill()
                    #         self.download_context.current_process.wait(timeout=3)
                    #     # print("Download process terminated")
                except Exception as e:
                    print(f"Error terminating process: {e}")
        except Exception as e:
            print(f"Cleanup error: {e}")
        finally:
            # self.join_threads()
            time.sleep(0.5)  # Give threads a moment to finish
            self.q_manager.cleanup()
            self.root.quit()
            self.root.destroy()

            if self.settings.get(
                "stream_and_merge_format"
            ) == "bestvideo+bestaudio/best-mp4" or not self.settings.get(
                "multisession_queue_download_support"
            ):
                if (
                    hasattr(self.download_context, "safe_title")
                    and self.download_context.safe_title
                ):
                    # base_name = self.download_context.safe_title.split(".")[0].strip()
                    base_name = self.download_service.get_base_name_from_ytdlp_file(
                        self.download_context.safe_title
                    )
                    if base_name:
                        self.download_service.cleanup_video_leftovers(
                            base_name, self.download_context.download_path_temp
                        )
                        self.add_to_delete_list(
                            base_name, self.download_context.download_path_temp
                        )

            self.cleanup_on_exit()

    def cancel_all_background_tasks(self):
        """Cancel ALL pending after() tasks"""
        if hasattr(self, "root") and self.root:
            try:
                # Get all pending job IDs and cancel them
                job_ids = self.root.tk.call("after", "info")
                for job_id in job_ids:
                    try:
                        self.root.after_cancel(job_id)
                    except:
                        pass
            except Exception as e:
                print(f"Error cancelling tasks: {e}")

    # def get_resource_path(self, relative_path):
    #     """Get absolute path to resource, works for dev and for PyInstaller"""
    #     try:
    #         # PyInstaller creates a temp folder and stores path in _MEIPASS
    #         base_path = sys._MEIPASS
    #     except Exception:
    #         base_path = os.path.dirname(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))))

    #     return os.path.join(base_path, relative_path)

    from pathlib import Path
    import subprocess, os

    def cleanup_on_exit(self):
        """Cross-platform cleanup using command line args"""

        files_to_delete = list(self.stopped_downloads_to_be_deleted)

        if not files_to_delete:
            return

        # Avoid deleting invalid placeholder
        if files_to_delete == [r'"Unknown Video"']:
            return

        utils_dir = Path(self.settings.get("utils_dir", "utils")).resolve()

        if os.name == "nt":  # Windows
            script_path = utils_dir / "cleanup_files.bat"
            cmd = [str(script_path)] + [str(f) for f in files_to_delete]
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)

        else:  # Linux / macOS
            script_path = utils_dir / "cleanup_files.sh"
            script_path = script_path.resolve()

            if not script_path.exists():
                print(f"Cleanup script not found: {script_path}")
                return

            # Make sure script is executable
            script_path.chmod(script_path.stat().st_mode | 0o111)

            # Build command as list, no quotes needed
            cmd = [str(script_path)] + [str(f) for f in files_to_delete]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    """Main application entry point"""

    try:

        downloader_app = VideoDownloaderApp()

        downloader_app.run()

    except Exception as e:

        print(f"Fatal error: {e}")

        messagebox.showerror("Fatal Error", f"Application failed to start:\n{str(e)}")

    finally:

        pass


if __name__ == "__main__":
    main()
