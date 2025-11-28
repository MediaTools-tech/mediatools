__version__ = "2.0.0"  # Current version
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
from mediatools.video.downloader.utils.tools import FFmpegTool, YtdlpTool
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
        # self.root.withdraw()

        self.settings = self.initialize_settings()
        first_run_setup(self.settings)
        self.ffmpeg_tool = FFmpegTool(self.settings)
        self.ytdlp_tool = YtdlpTool(self.settings)
        self.style_manager = PlatformStyleManager()
        self.q_manager = QueueManager(self.style_manager, self.root)

        self.ffmpeg_status = self.ffmpeg_tool.get_ffmpeg_status()
        self.ytdlp_status = self.ytdlp_tool.get_ytdlp_status()
        self.current_version_ytdlp = "Current version unkown"
        self.latest_version_ytdlp = "Latest version unknown"

        self.bin_dir = self.settings.get("bin_dir")
        self.ffmpeg_path = self.ffmpeg_status["ffmpeg_path"]
        self.ffprobe_path = self.ffmpeg_status["ffprobe_path"]
        self.ytdlp_path = self.ytdlp_status["ytdlp_path"]
        self.ffmpeg_update_running = False
        # self.aria2c_path = self.ytdlp_status["aria2c_path"]

        self.is_downloading = False
        self.latest_downloaded_video = None
        self.success_frame = None

        self.safe_title = "Unknown Video"  # Fallback title
        self.video_index = None
        self.total_videos = None
        self.files_downloaded = 0
        self.final_filename_check = ""
        self.is_playlist = False
        self.recent_url = ""
        self.download_path_temp = ""

        # Process control variables for pause/resume/stop functionality
        self.current_process = None
        self.current_download_url = None
        self.paused_url = None
        self.is_paused = False
        self.is_resumed = False
        self.is_stopped = False
        self.is_after_stopped = False
        self.download_thread = None
        self.stopped_downloads_to_be_deleted = []

        self.current_process = None
        self.is_downloading = False
        self.is_stopped = False
        self.is_exit = False

        self.progress_frame = None
        self.progress_bar = None
        self.status_label = None
        self.queue_status_label = None
        self.url_entry = None
        self.url_var = None
        self.buttons = None

        # self.status_lable_fg = "#68cdfe"
        self.status_label_fg = "#6c757d"

        self.custom_msg_box = CustomMessageBox()

        self.download_context = DownloadContext(
            download_folder=self.settings.get("downloads_dir"),
            update_status=self.update_status,
            update_queue_display=self.update_queue_display,
            gui_after=self.root.after,
            start_queue_processing=self.start_queue_processing,
            do_update_yt_dlp=self.do_update_yt_dlp,
            do_update_ffmpeg=self.do_update_ffmpeg,
            check_internet_connection=self.check_internet_connection,
            add_to_delete_list=self.add_to_delete_list,
            pause_resume_disable=self.pause_resume_disable,
            exit_app=self.exit_app,
            download_path_temp=self.download_path_temp,
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
            ffmpeg_status=self.ffmpeg_status,
            success_frame=self.success_frame,
            recent_url=self.recent_url,
            stopped_downloads_to_be_deleted=self.stopped_downloads_to_be_deleted,
            progress_bar=None,
            status_label_fg=None,
            download_type="video",
        )

        self.download_service = DownloadService(
            self.root,
            self.q_manager,
            self.settings,
            self.style_manager,
            self.custom_msg_box,
            self.download_context,
        )

        self.settings_gui_context = SettingsGUIContext(
            apply_theme_callabck=self.apply_theme
        )

        self.gui_context = GUIContext(
            progress_frame=self.progress_frame,
            progress_bar=self.progress_bar,
            status_label=self.status_label,
            status_label_fg=self.status_label_fg,
            queue_status_label=self.queue_status_label,
            url_entry=self.url_entry,
            url_var=self.url_var,
            buttons=self.buttons,
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
            # open_settings_guide=self.open_settings_guide,
            exit_app=self.exit_app,
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
        self.gui_context.resume_download_callback = (
            self.download_service.resume_download
        )
        self.gui_context.stop_download_callback = self.download_service.stop_download

        self.theme_manager.setup_gui()

        self.download_context.progress_bar = self.gui_context.progress_bar
        self.q_manager.set_gui_context(self.gui_context)

        # Fonts from style manager (with fallback)
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

        if not self.ytdlp_status["is_ytdlp_suite_installed"] and not self.settings.get(
            "auto_update"
        ):
            self.do_update()

        self.warning_label = tk.Label(
            self.root,
            text="Video Downloads - Pause/Resume supported only for: Format - bestvideo+bestaudio/best-mkv",
            fg="#000000",
            font=(self.label_font[0], self.label_font[1] - 1),
            bg=self.root.cget("bg"),
        )
        # self.settings.format_change_callback = self._update_buttons_based_on_format
        self._setup_subprocess_kwargs()

    def initialize_settings(self):
        """Initialize settings with robust fallback chain"""
        try:
            settings = SettingsManager()
            return settings

        except Exception as e:
            print(f"SettingsManager failed: {e}")

    # def _update_buttons_based_on_format(self):
    #     """Update buttons based on current format setting"""
    #     disable_pause_resume_flag = False
    #     if (
    #         self.download_context.is_downloading
    #         and self.download_context.download_type == "video"
    #     ):
    #         format_setting = self.settings.get(
    #             "stream_and_merge_format", "bestvideo+bestaudio/best-mp4"
    #         )
    #         disable_pause_resume_flag = (
    #             False if format_setting == "bestvideo+bestaudio/best-mkv" else True
    #         )

    #     self.pause_resume_disable(disable_pause_resume_flag)

    def pause_resume_disable(self, disable_pause_resume_flag):
        """Enable or disable pause/resume buttons"""
        state = "disabled" if disable_pause_resume_flag else "normal"

        # Show/hide warning
        if disable_pause_resume_flag:
            self.warning_label.place(x=162, y=387)
            self.warning_label.tkraise()
        else:
            self.warning_label.place_forget()  # Hide the warning

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

    # def open_settings_guide(self):
    #     """Open README file"""
    #     settings_guide_path = self.get_app_root() / "settings_guide.md"

    #     # if settings_guide_path.exists():
    #     if os.path.exists(settings_guide_path):
    #         self.open_file_safely(settings_guide_path)
    #     else:
    #         self.custom_msg_box.custom_showinfo(
    #             self.root,
    #             "Info",
    #             "Docs folder path not found",
    #             self.messagebox_font,
    #         )

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

    def open_queue_file(self):
        """Open queue file"""
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
        video_path = self.latest_downloaded_video
        if not video_path or not os.path.exists(video_path):
            video_path = self.get_latest_downloaded_video(
                self.settings.get("downloads_dir")
            )

        if video_path and os.path.exists(video_path):
            try:
                self.play_video(video_path)
            except Exception as e:
                # messagebox.showerror("Error", f"Could not play video: {e}")
                self.custom_msg_box.custom_showerror(
                    self.root,
                    "Error",
                    f"Could not play video: {e}",
                    self.messagebox_font,
                )
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

    def get_latest_downloaded_video(
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
                target=self.do_update(update_button_clicked), daemon=True
            ).start()

    def do_update(self, update_button_clicked=False):
        """Perform tool updates"""

        # App update check (once per week)
        if self.should_check_app_update():
            self.check_app_update()

        self.update_status(
            f"{self.style_manager.get_emoji('loading')} Wait...Checking yt-dlp status"
        )

        # self.root.update_idletasks()
        self.root.update()

        def ytdlp_callback(success, error=None):
            if success:
                self.check_ffmpeg()
            else:
                print(f"yt-dlp download failed: {error}")

        try:
            # Check and update yt-dlp
            if not os.path.exists(self.ytdlp_path):
                self.update_status(
                    f"{self.style_manager.get_emoji('error')} Yt-dlp Missing. Yt-dlp required to download videos",
                    error=True,
                )

                if self.custom_msg_box.custom_askyesno(
                    self.root,
                    "yt-dlp Missing",
                    "yt-dlp required to download videos.\n\nWould you like to download it now?",
                    self.messagebox_font,
                ):
                    self.do_update_yt_dlp(ytdlp_callback)
                else:
                    self.update_status(
                        "yt-dlp required to download videos, update to download",
                        error=True,
                    )
                    # self.root.update_idletasks()
                    self.root.update()
            else:

                # Get current version
                result = subprocess.run(
                    [self.ytdlp_path, "--version"],
                    timeout=30,
                    **self.kwargs,
                )
                if result.returncode != 0:
                    raise Exception("Failed to get current version")

                self.current_version_ytdlp = result.stdout.strip()

                # Fetch latest version from GitHub
                with urlopen(
                    self.ytdlp_status["ytdlp_github_api_latest"],
                    timeout=30,
                ) as response:
                    data = json.load(response)
                    self.latest_version_ytdlp = data["tag_name"]

                if self.current_version_ytdlp == self.latest_version_ytdlp:
                    self.update_status(
                        f"yt-dlp v{self.current_version_ytdlp} is up to date"
                    )
                    self.check_ffmpeg()
                else:
                    if self.custom_msg_box.custom_askyesno(
                        self.root,
                        "Yt-dlp Updated Version Available",
                        f"Update yt-dlp from {self.current_version_ytdlp} → {self.latest_version_ytdlp}?\n\nProceed?",
                        self.messagebox_font,
                    ):
                        self.do_update_yt_dlp(ytdlp_callback)

                if (
                    not self.settings.get("auto_update") or update_button_clicked
                ) and self.current_version_ytdlp == self.latest_version_ytdlp:

                    self.custom_msg_box.custom_showinfo(
                        self.root,
                        "Update Check",
                        f"Your yt-dlp version {self.current_version_ytdlp} is up to date!",
                        self.messagebox_font,
                    )

            self.update_status("")

        except Exception as e:
            self.root.after(0, lambda: self.gui_context.url_var.set(""))
            self.custom_msg_box.custom_showerror(
                self.root,
                "Update Error",
                f"Failed to check/update tools:\nCheck internet connection.\n{str(e)}",
                self.messagebox_font,
            )

            self.update_status("Update check failed", error=True)

    def should_check_app_update(self):
        """Check app updates once per week using date format"""
        import datetime

        # Get last check date (default to 0 if never checked)
        last_check_date = self.settings.get("last_app_update_check", 0)
        current_date = int(datetime.datetime.now().strftime("%Y%m%d"))

        try:
            # Check if 7 days have passed
            if current_date - last_check_date >= 7:
                self.settings.set("last_app_update_check", current_date)
                self.settings.save_settings()
                return True
        except:
            self.settings.set("last_app_update_check", current_date)
            self.settings.save_settings()
            return True
        return False

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
            print(f"Update check failed: {e}")

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

    def check_ffmpeg(self):
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
                # self.gui_context.buttons["download_btn"].config(state="disabled")

                self.do_update_ffmpeg()
            else:
                self.update_status(
                    "FFmpeg Missing. Settings option set: Video Format - b"
                )
                self.settings.set("stream_and_merge_format", "b")
                self.settings.save_settings()

        # FFmpeg found on system, but not downloadeed by video downloader, check installed FFmpeg version
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

                        self.do_update_ffmpeg()
                    else:
                        self.update_status(
                            "FFmpeg not updated, with outdated Fmpeg, video downloader may not work as expected",
                            percent=0,
                        )
                else:
                    self.update_status(
                        f"FFmpeg version {version_data} is compatible with video downloader {self.style_manager.get_emoji('check')}",
                        percent=0,
                    )
            else:
                self.update_status(
                    "Could not determine FFmpeg version, video downloader may not work as expected",
                    percent=0,
                )

        else:
            self.update_status("", percent=0)
            pass

        self.root.update()

    def get_ffmpeg_version(self):
        """Get FFmpeg version, handling both stable and development builds"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10,
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

    def _ffmpeg_update_success(self):
        """Called when FFmpeg update completes successfully"""
        # Update status and progress
        self.update_status(
            f"{self.style_manager.get_emoji('check')} FFmpeg downloaded/updated successfully!",
            percent=0,
        )

        # Refresh FFmpeg status
        self.download_context.ffmpeg_status = self.ffmpeg_tool.get_ffmpeg_status()

        # Re-enable button
        self.gui_context.buttons["update_btn"].config(state="normal")
        self.gui_context.buttons["download_btn"].config(state="normal")

        self.ffmpeg_update_running = False

        self.root.update()

        self.q_manager.check_previous_session(self.root)

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

        self.ffmpeg_update_running = False

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

    def do_update_yt_dlp(self, callback=None):
        """Perform the actual download and replacement of yt-dlp."""
        self.gui_context.buttons["update_btn"].config(state="disabled")
        self.gui_context.buttons["download_btn"].config(state="disabled")

        def ytdlp_thread():
            try:
                if os.path.exists(self.ytdlp_path):
                    # Backup old version
                    backup_path = self.get_backup_filename(self.ytdlp_path)
                    os.rename(self.ytdlp_path, backup_path)
                    print(f"Backed up old version to {backup_path}")

                url = self.ytdlp_status["ytdlp_latest_url"]
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
                    self.custom_msg_box.custom_showinfo(
                        self.root,
                        "Update Success",
                        f"Downloaded/Updated to yt-dlp v{version.stdout.strip()}",
                        self.messagebox_font,
                    )

                    self.gui_context.buttons["update_btn"].config(state="normal")
                    self.gui_context.buttons["download_btn"].config(state="normal")
                    callback(True)
                else:
                    self.gui_context.buttons["update_btn"].config(state="normal")
                    self.gui_context.buttons["download_btn"].config(state="normal")
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

                callback(False)

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

    def startup_functions(self):
        """Startup functions"""
        if self.settings.get("auto_update"):
            self.root.after(1000, self.do_update_then_continue)
        else:
            # If no auto-update, go straight to session check
            self.q_manager.check_previous_session(self.root)
        # self.queue_count = self.q_manager.get_queue_count()
        # self.failed_url_count = self.q_manager.get_failed_url_count()

    def do_update_then_continue(self):
        """Do update then continue with startup"""
        try:
            self.do_update()  # Your existing update function
        finally:
            if os.path.exists(self.ytdlp_path) and not self.ffmpeg_update_running:
                # Always continue with next step, even if update fails
                self.q_manager.check_previous_session(self.root)

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
            if self.download_context.current_process:
                try:
                    if self.download_context.current_process.poll() is None:
                        self.download_context.current_process.terminate()
                        try:
                            self.download_context.current_process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            self.download_context.current_process.kill()
                            self.download_context.current_process.wait(timeout=3)
                        # print("Download process terminated")
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

    # def cleanup_on_exit(self):
    #     """Cross-platform cleanup using command line args"""
    #     import subprocess
    #     import os
    #     import sys

    #     files_args = []
    #     for file_path in self.stopped_downloads_to_be_deleted:
    #             files_args.append(f'"{file_path}"')

    #     if not files_args:
    #         return

    #     utils_dir = self.settings.get("utils_dir", "utils")

    #     # Join all file arguments
    #     files_args_str = " ".join(files_args)
    #     if files_args_str == r'"Unknown Video"':
    #         return

    #     # Platform-specific command with hidden windows
    #     if os.name == 'nt':  # Windows
    #         script_path = (Path(utils_dir) / "cleanup_files.bat").resolve()
    #         cmd = f'"{script_path}" {files_args_str}'
    #         subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    #     else:  # Linux/Mac
    #         script_path = (Path(utils_dir) / "cleanup_files.sh").resolve()
    #         # Make sure script is executable
    #         subprocess.Popen(['chmod', '+x', script_path])
    #         cmd = f'"{script_path}" {files_args_str}'
    #         subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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
