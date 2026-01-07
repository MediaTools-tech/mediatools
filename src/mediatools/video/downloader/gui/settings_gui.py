import tkinter as tk
import os
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from mediatools.video.downloader.core.settings_manager import SettingsManager
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any


@dataclass
class SettingsGUIContext:
    """Contains all context needed for Settings GUI setup"""

    # GUI update functions
    apply_theme_callabck: Callable = None


class SettingsWindow:
    def __init__(
        self,
        parent,
        settings_manager,
        style_manager,
        custom_msg_box,
        context: SettingsGUIContext,
    ):
        self.parent = parent
        self.settings = settings_manager
        self.custom_msg_box = custom_msg_box
        self.window = None
        self.widgets = {}
        self.current_theme = self.settings.get("gui_theme", "Default")

        self.context = context
        # Store the last domain content to preserve it during toggles
        self._last_domain_content = ""

        self.style_manager = style_manager
        try:
            font_config = self.style_manager.get_font_config("label")
            self.label_font = (font_config["family"], font_config["size"])
        except Exception:
            self.label_font = ("Arial", 9)

        try:
            font_config = self.style_manager.get_font_config("messagebox")
            self.messagebox_font = (font_config["family"], font_config["size"])
        except Exception:
            self.messagebox_font = ("Arial", 10)

        try:
            font_config = self.style_manager.get_font_config("title")
            self.title_font = (font_config["family"], font_config["size"])
        except Exception:
            self.title_font = ("Arial", 10)

    def open(self):
        """Open the settings window"""

        if not hasattr(self, "style") or self.style is None:
            self.style = ttk.Style()
            self.style.theme_use("clam")

        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Downloader Settings")
        self.window.geometry("550x770")
        self.window.resizable(False, False)

        # Explicit background for the window
        self.window.configure(bg="#f0f0f0")  # light gray (hex)

        self._create_widgets()
        self._load_current_settings()

    def _create_widgets(self):
        """Create all settings widgets"""
        # Main frame (no scrolling needed)
        main_frame = tk.Frame(self.window, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Content frame (replaces scrollable_frame)
        content_frame = tk.Frame(main_frame, bg="#f0f0f0")
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            content_frame,  # Changed from scrollable_frame to content_frame
            text="Downloader Settings",
            font=(self.title_font[0], self.title_font[1] + 2, "bold"),
            foreground="#0047AB",
            background="#f0f0f0",
            anchor="w",
        ).pack(pady=(0, 10), fill="x", padx=5)

        # Info label
        info_label = tk.Label(
            content_frame,  # Changed from scrollable_frame to content_frame
            text="Check Readme for detail description of settings parameters",
            font=(self.label_font[0], self.label_font[1], "italic"),
            foreground="#292929",
            background="#f0f0f0",
            anchor="w",
        )
        info_label.pack(pady=(0, 10), fill="x", padx=5)

        scrollable_frame = content_frame

        # Auto Update
        self._create_dropdown(
            scrollable_frame, "Auto update:", "auto_update", ["True", "False"], 
            0
        )

        # Limit Rate
        self._create_entry(
            scrollable_frame, "Limit rate:", "download_speed", "e.g. 5M, 2M", 
            1
        )

        # Format
        self._create_dropdown(
            scrollable_frame,
            "Video/Audio file format:",
            "stream_and_merge_format",  # New key name
            [
                "bestvideo+bestaudio/best-mkv",
                "bestvideo+bestaudio/best-mp4",
                "b",
            ],
            2,
        )

        # Audio Format
        self._create_dropdown(
            scrollable_frame,
            "Audio only file format:",
            "audio_format",
            ["m4a", "mp3", "bestaudio"],
            3,
        )

        # Embed thumbnail in audio file
        self._create_dropdown(
            scrollable_frame,
            "Embed thumbnail in audio file:",
            "embed_thumbnail_in_audio",
            [
                "Yes",
                "No",
            ],
            4,
        )

        # Download Archive
        self._create_dropdown(
            scrollable_frame,
            "Download archive:",
            "enable_download_archive",
            ["True", "False"],
            5,
        )

        # Multisession Queue Support
        self._create_dropdown(
            scrollable_frame,
            "Multisession queue support:",
            "multisession_queue_download_support",
            ["True", "False"],
            6,
        )

        # Track Failed URL
        self._create_dropdown(
            scrollable_frame,
            "Track failed URL:",
            "track_failed_url",
            ["True", "False"],
            7,
        )

        # Cookies from Browser
        self._create_browser_dropdown(
            scrollable_frame,
            "Cookies from browser:",
            "enable_cookies_from_browser",
            "cookies_browser",
            8,
        )

        # Browser Profile/Path (with browse file button)
        self._create_path_entry(
            scrollable_frame,
            "Browser profile/path:",
            "cookies_browser_profile",
            "Select browser profile file",
            9,
            file_types=[("All files", "*.*")],
        )

        # Cookies File Path
        self._create_path_entry(
            scrollable_frame,
            "Cookies file path:",
            "cookies_path",
            "Select cookies.txt file",
            10,
            file_types=[("Text files", "*.txt")],
        )

        # GUI theme
        self._create_dropdown(
            scrollable_frame,
            "GUI Theme:",
            "gui_theme",
            [
                "Default",
                "Dark",
                "Unicolor_1",
                "Unicolor_2",
                "Unicolor_3",
                "Minimalist_1",
                "Minimalist_2",
                "Minimalist_3",
            ],
            11,
        )

        # Download Path
        self._create_path_entry(
            scrollable_frame,
            "Download path:",
            "downloads_dir",
            "Select download directory",
            12,
        )

        # Download in Subfolders
        self._create_dropdown(
            scrollable_frame,
            "Download in subfolders:",
            "platform_specific_download_folders",
            ["True", "False"],
            13,
        )

        # Spotify Client ID
        self._create_entry(
            scrollable_frame, "Spotify Client ID:", "spotify_client_id", "e.g., a1b2c3d4e5f67890a1b2c3d4e5f67890", 
            14
        )

        # Spotify Client ID
        self._create_entry(
            scrollable_frame, "Spotify Client Secret:", "spotify_client_secret", "e.g., c0ffee1234567890abcdeffedcba9876", 
            15
        )

        # Spotify OAuth checkbox
        self._create_checkbox(
            scrollable_frame,
            "Enable spotify playlist downloads(Need onetime OAuth setup - Check UserGuide):",
            "enable_spotify_playlist",
            "spotify_playlist",
            16,
        )

        # Button frame - ALWAYS PACKED LAST
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=10)

        # All buttons with takefocus=0 (no focus indicators)
        reset_btn = ttk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self._reset_to_defaults,
            takefocus=0,  # No focus, no dotted border
        )
        reset_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Apply",
            command=self._apply_settings,
            takefocus=0,  # Apply to all buttons
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.window.destroy,
            takefocus=0,  # Apply to all buttons
        ).pack(side=tk.RIGHT, padx=5)

    # def _toggle_domain_entry(self, *args):
    #     """Show/hide domain entry when subfolder option is toggled"""
    #     if self.widgets["platform_specific_download_folders"].get() == "True":
    #         # Show the domain frame
    #         self.domain_frame.pack(
    #             fill=tk.X, pady=5, before=self.domain_frame.master.winfo_children()[-1]
    #         )

    #         domain_entry = self.widgets["subfolder_domains"]
    #         current_text = domain_entry.get("1.0", tk.END).strip()

    #         # If widget is empty, try to restore last content or use defaults
    #         if current_text == "":
    #             if self._last_domain_content.strip():
    #                 # Restore previously entered content
    #                 domain_entry.insert("1.0", self._last_domain_content)
    #             else:
    #                 # Use defaults only if no previous content exists
    #                 domain_entry.insert("1.0", "youtube.com,x.com")
    #     else:
    #         # Before hiding, save the current content
    #         domain_entry = self.widgets["subfolder_domains"]
    #         self._last_domain_content = domain_entry.get("1.0", tk.END).strip()
    #         self.domain_frame.pack_forget()

    def _load_current_settings(self):
        """Load current settings into the UI widgets"""
        current = self.settings.current_settings

        # Load all basic settings
        self.widgets["auto_update"].set(str(current.get("auto_update", True)))
        self.widgets["downloads_dir"].set(current.get("downloads_dir", ""))

        # Handle download speed - clear placeholder if it's a real value
        speed_value = current.get("download_speed", "5M")
        self.widgets["download_speed"].set(speed_value)

        self.widgets["enable_download_archive"].set(
            str(current.get("enable_download_archive", False))
        )
        format_value = current.get(
            "stream_and_merge_format", "bestvideo+bestaudio/best-mkv"
        )
        self.widgets["stream_and_merge_format"].set(format_value)

        audio_format_value = current.get("audio_format", "m4a")
        self.widgets["audio_format"].set(audio_format_value)

        embed_thumbnail_in_audio = current.get("embed_thumbnail_in_audio", "Yes")
        self.widgets["embed_thumbnail_in_audio"].set(embed_thumbnail_in_audio)

        self.widgets["multisession_queue_download_support"].set(
            str(current.get("multisession_queue_download_support", True))
        )
        self.widgets["track_failed_url"].set(str(current.get("track_failed_url", True)))

        # Load browser cookies settings
        self.widgets["enable_cookies_from_browser"].set(
            current.get("enable_cookies_from_browser", False)
        )
        self.widgets["cookies_browser"].set(current.get("cookies_browser", "chrome"))
        self.widgets["cookies_browser_profile"].set(
            current.get("cookies_browser_profile", "")
        )
        self.widgets["cookies_path"].set(current.get("cookies_path", ""))

        # Load theme from string value (not boolean flags)
        theme_value = current.get("gui_theme", "Default")
        self.widgets["gui_theme"].set(theme_value)

        # Load subfolder settings and handle domain entry visibility
        platform_folders_enabled = current.get(
            "platform_specific_download_folders", False
        )
        self.widgets["platform_specific_download_folders"].set(
            str(platform_folders_enabled)
        )
        client_id = current.get("spotify_client_id", "")
        self.widgets["spotify_client_id"].set(client_id)
        client_secret = current.get("spotify_client_secret", "")
        self.widgets["spotify_client_secret"].set(client_secret)
        self.widgets["enable_spotify_playlist"].set(
            current.get("enable_spotify_playlist", False)
        )



    def _create_dropdown(self, parent, label_text, setting_key, options, row):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text=label_text, width=27).pack(side=tk.LEFT)

        var = tk.StringVar()
        combobox = ttk.Combobox(
            frame, textvariable=var, values=options, state="readonly", width=20
        )
        combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        self.widgets[setting_key] = var

    def _create_entry(self, parent, label_text, setting_key, placeholder, row):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        ttk.Label(frame, text=label_text, width=27).pack(side=tk.LEFT)
        var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=var, width=30)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        entry.insert(0, placeholder)
        entry.config(foreground="#333333")

        def on_focus_in(event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(foreground="black")

        def on_focus_out(event):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.config(foreground="gray")

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

        # Store both the StringVar and the Entry widget
        self.widgets[setting_key] = var
        self.widgets[f"{setting_key}_entry"] = entry

    def _create_path_entry(
        self, parent, label_text, setting_key, button_text, row, file_types=None
    ):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text=label_text, width=27).pack(side=tk.LEFT)

        var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=var, width=25)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))

        browse_text = "Browse File" if file_types else "Browse Folder"
        ttk.Button(
            frame,
            text=browse_text,
            command=lambda: self._browse_path(var, setting_key, file_types),
        ).pack(side=tk.RIGHT)

        self.widgets[setting_key] = var

    def _create_browser_dropdown(
        self, parent, label_text, enable_key, browser_key, row
    ):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text=label_text, width=27).pack(side=tk.LEFT)

        enable_var = tk.BooleanVar()
        enable_cb = tk.Checkbutton(
            frame,
            text="Enable",
            variable=enable_var,
            onvalue=True,
            offvalue=False,
            bg="#d3d3d3",
        )
        enable_cb.pack(side=tk.LEFT, padx=(0, 10))

        browser_var = tk.StringVar()
        browsers = [
            "chrome",
            "firefox",
            "safari",
            "brave",
            "edge",
            "opera",
            "chromium",
            "vivaldi",
            "whale",
        ]
        browser_cb = ttk.Combobox(
            frame, textvariable=browser_var, values=browsers, state="readonly", width=15
        )
        browser_cb.pack(side=tk.LEFT)

        self.widgets[enable_key] = enable_var
        self.widgets[browser_key] = browser_var


    def _create_checkbox(
        self, parent, label_text, enable_key, browser_key, row
    ):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text=label_text, width=75).pack(side=tk.LEFT)

        enable_var = tk.BooleanVar()
        enable_cb = tk.Checkbutton(
            frame,
            text="Enable",
            variable=enable_var,
            onvalue=True,
            offvalue=False,
            bg="#d3d3d3",
        )
        enable_cb.pack(side=tk.RIGHT, padx=(0, 10))
        self.widgets[enable_key] = enable_var

    def _browse_path(self, var, setting_key=None, file_types=None):
        if setting_key == "cookies_path":
            initial_path = (
                os.path.dirname(self.settings.get("cookies_path"))
                if self.settings.get("cookies_path")
                else self.settings.get("data_path")
            )
        elif setting_key == "cookies_browser_profile":
            initial_path = (
                os.path.dirname(self.settings.get("cookies_browser_profile"))
                if self.settings.get("cookies_browser_profile")
                else self.settings.get("data_path")
            )
        else:
            initial_path = var.get() or str(Path.home())

        if file_types:
            path = filedialog.askopenfilename(
                initialdir=initial_path, filetypes=file_types, title="Select File"
            )
        else:
            path = filedialog.askdirectory(
                initialdir=initial_path, title="Select Directory"
            )
        if path:
            var.set(path)

    def _reset_to_defaults(self):
        if self.custom_msg_box.custom_askyesno(
            self.parent,
            "Confirm Reset",
            "Are you sure you want to reset all settings to defaults?",
            self.messagebox_font,
        ):
            self.settings.reset_to_defaults()
            self._load_current_settings()
            self.custom_msg_box.custom_showinfo(
                self.parent,
                "Reset Complete",
                "Settings have been reset to defaults.",
                self.messagebox_font,
            )
            self.window.destroy()  # close window like Apply

    def _apply_settings(self):
        try:
            # Get current domain content and save it to our temporary storage
            # if "subfolder_domains" in self.widgets:
            #     current_domains = (
            #         self.widgets["subfolder_domains"].get("1.0", tk.END).strip()
            #     )
            #     self._last_domain_content = current_domains

            downloads_dir_cleaned = self.clean_path_field(
                self.widgets["downloads_dir"].get()
            )
            cookies_path_cleaned = self.clean_path_field(
                self.widgets["cookies_path"].get()
            )
            cookies_browser_profile_cleaned = self.clean_path_field(
                self.widgets["cookies_browser_profile"].get()
            )

            new_settings = {
                "auto_update": self.widgets["auto_update"].get() == "True",
                "downloads_dir": downloads_dir_cleaned,
                "download_speed": self.widgets["download_speed"].get(),
                "enable_download_archive": self.widgets["enable_download_archive"].get()
                == "True",
                "stream_and_merge_format": self.widgets[
                    "stream_and_merge_format"
                ].get(),
                "audio_format": self.widgets["audio_format"].get(),
                "embed_thumbnail_in_audio": self.widgets[
                    "embed_thumbnail_in_audio"
                ].get(),
                "multisession_queue_download_support": self.widgets[
                    "multisession_queue_download_support"
                ].get()
                == "True",
                "track_failed_url": self.widgets["track_failed_url"].get() == "True",
                "enable_cookies_from_browser": self.widgets[
                    "enable_cookies_from_browser"
                ].get(),
                "cookies_browser": self.widgets["cookies_browser"].get(),
                "cookies_browser_profile": cookies_browser_profile_cleaned,
                "cookies_path": cookies_path_cleaned,
                "gui_theme": self.widgets["gui_theme"].get(),
                "platform_specific_download_folders": self.widgets[
                    "platform_specific_download_folders"
                ].get()
                == "True",
                "spotify_client_id": self.widgets["spotify_client_id"].get(),
                "spotify_client_secret": self.widgets["spotify_client_secret"].get(),
                "enable_spotify_playlist": self.widgets[
                    "enable_spotify_playlist"
                ].get(),

            }

            if self.settings.save_settings(new_settings):
                # self.custom_msg_box.custom_showinfo(
                #     self.parent,
                #     "Success",
                #     "Settings have been saved successfully.",
                #     self.messagebox_font,
                # )
                self.window.destroy()
            else:
                self.custom_msg_box.custom_showerror(
                    self.parent,
                    "Error",
                    "Failed to save settings.",
                    self.messagebox_font,
                )

            try:
                # Get the new theme
                new_theme = self.widgets["gui_theme"].get()

                # Check if theme actually changed
                if new_theme != self.current_theme:
                    self.current_theme = new_theme
                    self.context.apply_theme_callabck()

            except Exception as e:
                print(f"Error applying settings: {e}")

        except Exception as e:
            self.custom_msg_box.custom_showerror(
                self.parent,
                "Error",
                f"An error occurred while saving settings: {str(e)}",
                self.messagebox_font,
            )

    def clean_path_field(self, path_string):
        """Clean path field, ensuring empty strings stay empty"""
        if not path_string or not str(path_string).strip():
            return ""

        cleaned = str(path_string).strip().strip('"').strip("'")
        return str(Path(cleaned)) if cleaned else ""
