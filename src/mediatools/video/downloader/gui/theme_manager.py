import os
import sys
import platform
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any
from pathlib import Path

# Determine platform
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


@dataclass
class GUIContext:
    """Contains all context needed for GUI setup"""

    progress_frame: object
    progress_bar: object
    status_label: object
    status_label_fg: str
    queue_status_label: object  #
    url_entry: object
    url_var: object
    buttons: object
    # buttons: Dict[str, ttk.Button] = {}

    # GUI update functions
    add_url_to_queue: Optional[Callable] = None
    pause_download_callback: Optional[Callable] = None
    resume_download_callback: Optional[Callable] = None
    stop_download_callback: Optional[Callable] = None
    update_tools: Optional[Callable] = None
    play_latest_video: Optional[Callable] = None
    open_folder: Optional[Callable] = None
    open_failed_url_file: Optional[Callable] = None
    open_queue_file: Optional[Callable] = None
    open_settings_gui: Optional[Callable] = None
    # open_settings_guide: Optional[Callable] = None
    exit_app: Optional[Callable] = None


class ThemeManager:
    """GUI theme manager"""

    def __init__(
        self,
        root,
        queue_manager,
        settings,
        style_manager,
        download_context,
        context: GUIContext,
    ):
        self.q_manager = queue_manager
        self.context = context
        self.settings = settings
        self.root = root
        self.style_manager = style_manager
        font_config = None
        self.common_font = None
        self.download_context = download_context

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

    def setup_gui(self):
        """Setup the main application GUI"""
        self.root.title("MediaTools Video Downloader v2.1.0")
        self.root.geometry("800x420")
        self.gui_window_bg = "#f8f9fa"
        self.root.configure(bg=self.gui_window_bg)  # Light gray background
        self.root.resizable(False, False)

        # Then in your icon loading code:
        try:

            assets_dir = Path(self.settings.get("assets_dir", "assets"))

            # Platform-specific icon paths
            system = platform.system()
            if system == "Windows":
                icon_path = assets_dir / "icon.ico"
                self.root.iconbitmap(str(icon_path))
            elif system == "Darwin":
                icon_path = assets_dir / "icon.png"
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.tk.call("wm", "iconphoto", self.root._w, icon)
            else:  # Linux
                icon_path = assets_dir / "icon_32x32.png"
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, icon)
                self.root._icon = icon
        except Exception as e:
            print(f"Could not load window icon: {e}")

        # Create main layout with correct proportions
        self.create_main_layout()
        self.create_button_panels()
        self.setup_styles()
        self.setup_bindings()

    def resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        # Make sure frozen check comes first
        base_path = ""
        if getattr(sys, "frozen", False):
            # PyInstaller build (onefile or onedir)
            exe_dir = Path(sys.executable).parent
            if (exe_dir / "_internal").exists():
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = sys._MEIPASS
        else:
            # Development
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Handle Windows vs Linux path separators
        if os.name == "nt":  # Windows
            return os.path.join(base_path, relative_path.replace("/", "\\"))
        else:  # Linux/Mac
            return os.path.join(base_path, relative_path.replace("\\", "/"))

    def setup_styles(self):
        """Setup styles based on current theme"""
        theme = self.settings.get("gui_theme", "Default")
        self.set_gui_window_bg_fg(theme)
        self.set_download_buttom_img(theme)

        if theme == "Minimalist_1":
            self.setup_styles_minimal()
        elif "Unicolor" in theme or theme == "Minimalist_2" or theme == "Minimalist_3":
            self.setup_styles_unicolor(theme)
        elif theme == "Dark":
            self.setup_styles_dark()
        else:
            self.setup_styles_default()

    def set_download_buttom_img(self, theme="Default"):
        assets_dir = Path(self.settings.get("assets_dir", "assets"))

        theme_download_btn_img_mapping: Dict[str, str] = {
            "Default": "d1.gif",
            "Dark": "d2.gif",
            "Unicolor_1": "u1.gif",
            "Unicolor_2": "u2.gif",
            "Unicolor_3": "u3.gif",
            "Minimalist_1": "m12.gif",
            "Minimalist_2": "m12.gif",
            "Minimalist_3": "m3.gif",
        }

        download_button_icon_path = assets_dir / theme_download_btn_img_mapping.get(
            theme, "d1.gif"
        )

        try:

            self.download_button_icon = tk.PhotoImage(
                file=str(download_button_icon_path)
            )

        except Exception:

            self.download_button_icon = tk.PhotoImage(width=20, height=20)

    def set_gui_window_bg_fg(self, theme="Default"):
        """Set bg and fg colors for all widgets, except buttons"""
        if not hasattr(self, "style") or self.style is None:
            self.style = ttk.Style()
            self.style.theme_use("clam")

        if theme == "Default":
            gui_window_bg = "#f8f9fa"
            url_frame_bg = None
            url_frame_label_bg_fg = ("#f8f9fa", "#04448a")
            url_entry_bg_fg_fbg = ("#e9ecef", "#004da0", "#f8f9fa")  # 495057
            border_colors = ("#bbbbbb", "#cccccc")
            progress_frame_bg = None
            progress_bar_bg_tc_bc = ("#02aa20", "#e9ecef", "#e9ecef")  # fg, bg, border
            footer_fg = ("#6c757d",)
            self.context.status_label_fg = "#004da0"
            self.download_context.status_label_fg = "#004da0"
            url_entry_borderwidth = 0
        elif "Unicolor" in theme or theme == "Minimalist_2" or theme == "Minimalist_3":
            bg_color, fg_color = self.get_unicolor_bg_fg(theme)
            gui_window_bg = "#f8f9fa"
            url_frame_bg = None
            url_frame_label_bg_fg = (
                ("#f8f9fa", bg_color) if "Unicolor" in theme else ("#f8f9fa", fg_color)
            )
            url_entry_bg_fg_fbg = ("#e9ecef", "#767777", "#f8f9fa")  # 495057
            progress_frame_bg = None
            progress_bar_bg_tc_bc = (
                "#4285F4" if "Minimalist" in theme else bg_color,
                "#e9ecef",
                "#e9ecef",
            )
            footer_fg = ("#6c757d",)
            self.context.status_label_fg = "#495057"
            self.download_context.status_label_fg = "#495057"
            url_entry_borderwidth = 1
            border_colors = ("#bbbbbb", "#cccccc")
        elif theme == "Minimalist_1":
            gui_window_bg = "#f8f9fa"
            url_frame_bg = None
            url_frame_label_bg_fg = ("#f8f9fa", "#495057")
            url_entry_bg_fg_fbg = ("#e9ecef", "#007bff", "#e9ecef")  # 495057
            progress_frame_bg = None
            progress_bar_bg_tc_bc = ("#6D7680", "#e9ecef", "#e9ecef")
            footer_fg = ("#6c757d",)
            self.context.status_label_fg = "#495057"
            self.download_context.status_label_fg = "#495057"
            url_entry_borderwidth = 0
            border_colors = ("#e9ecef", "#e9ecef")
        elif theme == "Dark":
            gui_window_bg = "#202940"
            url_frame_bg = None
            url_frame_label_bg_fg = ("#222a3f", "#dcb862")
            url_entry_bg_fg_fbg = ("#222a3f", "#68cdfe", "#323a4f")  # 495057
            progress_frame_bg = None
            progress_bar_bg_tc_bc = ("#005DC1", "#222a3f", "#222a3f")
            footer_fg = ("#6c757d",)
            self.context.status_label_fg = "#68cdfe"
            self.download_context.status_label_fg = "#68cdfe"
            url_entry_borderwidth = 0
            border_colors = ("#323a4f", "#323a4f")
        else:
            print("Error: Unrecognized theme.")

        # Set defaults to avoid redundancy
        if url_frame_bg is None:
            url_frame_bg = gui_window_bg
        if progress_frame_bg is None:
            progress_frame_bg = gui_window_bg

        self.gui_window_bg = gui_window_bg
        self.grid_container.configure(bg=gui_window_bg)
        self.root.configure(bg=gui_window_bg)
        self.main_frame.configure(bg=gui_window_bg)
        self.tk_label.configure(
            bg=url_frame_label_bg_fg[0], fg=url_frame_label_bg_fg[1]
        )

        self.url_frame.configure(bg=gui_window_bg)
        self.progress_frame.configure(bg=progress_frame_bg)
        self.context.status_label.configure(bg=gui_window_bg)
        self.context.queue_status_label.configure(bg=gui_window_bg)
        self.footer.configure(bg=gui_window_bg, fg=footer_fg)

        # CANVAS PROGRESS BAR THEMING (replaces ttk style configuration)
        if hasattr(self, "progress_canvas"):
            self.progress_canvas.configure(
                bg=progress_bar_bg_tc_bc[1]
            )  # Trough background
            self.progress_canvas.itemconfig(
                self.progress_rect, fill=progress_bar_bg_tc_bc[0]
            )  # Progress color

        self.style.configure(
            "Url.TEntry",
            borderwidth=url_entry_borderwidth,
            focuscolor="none",
            foreground=url_entry_bg_fg_fbg[1],
            background=url_entry_bg_fg_fbg[0],
            fieldbackground=url_entry_bg_fg_fbg[0],
            font=self.label_font,
        )

        self.style.map(
            "Url.TEntry",
            fieldbackground=[
                ("readonly", url_entry_bg_fg_fbg[2]),
                ("active", url_entry_bg_fg_fbg[2]),
                ("!disabled", url_entry_bg_fg_fbg[2]),
            ],
            bordercolor=[
                ("focus", border_colors[0]),
                ("!focus", border_colors[1]),
            ],
            lightcolor=[("", url_entry_bg_fg_fbg[2])],
            darkcolor=[("", url_entry_bg_fg_fbg[2])],
        )

        return

    def setup_styles_default(self):
        """Configure modern button styles"""

        primary_btn_bg_color = "#0b81d1"
        primary_btn_fg_color = "white"

        # Configure colors and fonts
        self.style.configure(
            "Primary.TButton",
            font=self.button_font,
            background=primary_btn_bg_color,
            foreground=primary_btn_fg_color,
            padding=(5, 5),
            borderwidth=0,
            focuscolor="none",
        )

        self.style.configure(
            "Primary.TButton", image=self.download_button_icon, compound="left"
        )

        color_set = [
            "#1fb4c2",
            "#6E5DC6",
            "#8ba820",
            "#E86100",
            "#bb950b",
            "#0b81d1",
            "#9f9b62",
            "#c04652",
            "#28a745",
            "#E86100",
            "#dc3545",
            "#dc3545",
        ]

        # Dynamically create styles for buttons
        for i in range(0, 11):
            self.style.configure(
                f"Secondary{i}.TButton",
                font=self.button_font,
                background=color_set[i],  # Use i-1 to index from 0
                foreground="white",
                padding=(5, 5),
                borderwidth=0,
                focuscolor="none",
            )

            # Add hover effects for each style
            self.style.map(
                f"Secondary{i}.TButton",
                background=[
                    ("active", self.darken_color(color_set[i])),
                    ("pressed", self.lighten_color(color_set[i])),
                ],
            )

        # Hover effects
        self.style.map(
            "Primary.TButton",
            background=[
                ("active", self.darken_color(primary_btn_bg_color)),
                ("pressed", self.lighten_color(primary_btn_bg_color)),
            ],
        )

    def setup_styles_minimal(self):
        """Configure modern button styles"""
        if not hasattr(self, "style") or self.style is None:
            self.style = ttk.Style()
            self.style.theme_use("clam")

        bg_color_primary, fg_color_primary = "#e9ecef", "#2f2f2f"
        bg_color_secondary, fg_color_secondary = "#e9ecef", "#2f2f2f"

        # Configure colors and fonts
        self.style.configure(
            "Primary.TButton",
            background=bg_color_primary,
            font=self.button_font,
            foreground=fg_color_primary,
            padding=(5, 5),
            borderwidth=0,
            focuscolor="none",
        )

        self.style.configure(
            "Primary.TButton", image=self.download_button_icon, compound="left"
        )

        # Dynamically create styles for buttons
        for i in range(0, 11):
            self.style.configure(
                f"Secondary{i}.TButton",
                font=self.button_font,
                background=bg_color_secondary,
                foreground=fg_color_secondary,
                padding=(5, 5),
                borderwidth=0,
                focuscolor="none",
            )

            # Hover effects
            # Add hover effects for each style
            self.style.map(
                f"Secondary{i}.TButton",
                background=[
                    ("active", self.darken_color(bg_color_secondary, 0.1)),
                    ("pressed", self.lighten_color(fg_color_secondary, 0.1)),
                ],
            )

        # Hover effects
        self.style.map(
            "Primary.TButton",
            background=[
                ("active", self.darken_color(bg_color_primary, 0.1)),
                ("pressed", self.lighten_color(fg_color_primary, 0.1)),
            ],
        )

    def setup_styles_unicolor(self, theme):
        """Configure modern button styles"""
        if not hasattr(self, "style") or self.style is None:
            self.style = ttk.Style()
            self.style.theme_use("clam")

        bg_color_primary, fg_color_primary = self.get_unicolor_bg_fg(theme)
        bg_color_secondary, fg_color_secondary = self.get_unicolor_bg_fg(theme)

        # Configure colors and fonts
        self.style.configure(
            "Primary.TButton",
            background=bg_color_primary,
            font=self.button_font,
            foreground=fg_color_primary,
            padding=(5, 5),
            borderwidth=0,
            focuscolor="none",
        )

        self.style.configure(
            "Primary.TButton", image=self.download_button_icon, compound="left"
        )

        # Dynamically create styles for buttons
        for i in range(0, 11):
            self.style.configure(
                f"Secondary{i}.TButton",
                font=self.button_font,
                background=bg_color_secondary,
                foreground=fg_color_secondary,
                padding=(5, 5),
                borderwidth=0,
                focuscolor="none",
            )

            hover_factor = 0.1 if "Minimalist" in theme else 0.2

            # Hover effects
            self.style.map(
                f"Secondary{i}.TButton",
                background=[
                    ("active", self.darken_color(bg_color_secondary, hover_factor)),
                    ("pressed", self.lighten_color(fg_color_secondary, hover_factor)),
                ],
            )

        # Hover effects
        self.style.map(
            "Primary.TButton",
            background=[
                ("active", self.darken_color(bg_color_primary, hover_factor)),
                ("pressed", self.lighten_color(fg_color_primary, hover_factor)),
            ],
        )

    def get_unicolor_bg_fg(self, theme):
        """unicolor theme with specific color set"""
        color_sets = {
            "Unicolor_1": {"bg": "#3E74CA", "fg": "#ffffff"},
            "Unicolor_2": {"bg": "#7fa85a", "fg": "#f7f9ec"},
            "Unicolor_3": {"bg": "#a2a143", "fg": "#f8faf7"},
            "Minimalist_2": {"bg": "#f0f2f1", "fg": "#374139"},
            "Minimalist_3": {"bg": "#ebebeb", "fg": "#3E74CA"},
        }
        return color_sets[theme]["bg"], color_sets[theme]["fg"]

    def setup_styles_dark(self):
        """Configure modern button styles"""

        bg_color_hex_primary = "#323a4f"
        fg_color_hex_primary = "#e8e8e8"

        bg_color_hex_secondary = "#323a4f"
        fg_color_hex_secondary = "#e8e8e8"

        # Configure colors and fonts
        self.style.configure(
            "Primary.TButton",
            background=bg_color_hex_primary,
            font=self.button_font,
            foreground=fg_color_hex_primary,
            padding=(5, 5),
            borderwidth=0,
            focuscolor="none",
        )

        self.style.configure(
            "Primary.TButton", image=self.download_button_icon, compound="left"
        )

        # Dynamically create styles for buttons
        for i in range(0, 11):
            self.style.configure(
                f"Secondary{i}.TButton",
                font=self.button_font,
                background=bg_color_hex_secondary,
                foreground=fg_color_hex_secondary,
                padding=(5, 5),
                borderwidth=0,
                focuscolor="none",
            )

            # Hover effects
            # Add hover effects for each style
            self.style.map(
                f"Secondary{i}.TButton",
                background=[
                    ("active", self.darken_color(bg_color_hex_secondary)),
                    ("pressed", self.lighten_color(bg_color_hex_secondary)),
                ],
            )

        # Hover effects
        self.style.map(
            "Primary.TButton",
            background=[
                ("active", self.darken_color(bg_color_hex_primary)),
                ("pressed", self.lighten_color(bg_color_hex_primary)),
            ],
        )

    def lighten_color(self, hex_color, factor=0.2):
        """Lighten a color by a given factor"""
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        light_rgb = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
        return f"#{light_rgb[0]:02x}{light_rgb[1]:02x}{light_rgb[2]:02x}"

    def darken_color(self, hex_color, factor=0.2):
        """Darken a color by a given factor"""
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        dark_rgb = tuple(max(0, int(c * (1 - factor))) for c in rgb)
        return f"#{dark_rgb[0]:02x}{dark_rgb[1]:02x}{dark_rgb[2]:02x}"

    def create_main_layout(self):
        """Create the main layout structure with 40-60 split"""
        self.main_frame = tk.Frame(
            self.root, bg=self.gui_window_bg, relief="flat", bd=1
        )
        self.main_frame.pack(fill="x", padx=20, pady=(25, 5))
        self.main_frame.pack_propagate(True)

        # URL input section
        self.url_frame = tk.Frame(self.main_frame, bg=self.gui_window_bg)
        self.url_frame.pack(fill="x", pady=(5, 10), padx=30)

        self.tk_label = tk.Label(
            self.url_frame,
            text="Enter Video URL:",
            bg=self.gui_window_bg,
            fg="#495057",
            font=self.label_font,
        )
        self.tk_label.pack(anchor="w")

        # Entry with StringVar
        self.context.url_var = tk.StringVar(value="")  # Default value
        self.context.url_entry = ttk.Entry(
            self.url_frame,
            textvariable=self.context.url_var,
            font=self.label_font,
            style="Url.TEntry",
        )
        self.context.url_entry.pack(fill="x", pady=(2, 15))
        self.context.url_entry.focus_set()

        # Status label ABOVE progress bar
        self.context.status_label = tk.Label(
            self.main_frame,
            text="",
            font=self.label_font,
            fg="#007bff",
            anchor="w",
            bg=self.gui_window_bg,
        )
        self.context.status_label.pack(fill="x", padx=30, pady=(0, 3))

        self.progress_frame = tk.Frame(self.main_frame, bg=self.gui_window_bg, height=8)
        self.progress_frame.pack(fill="x", pady=(3, 1), padx=32)
        self.progress_frame.pack_propagate(True)  # Maintain height

        self.progress_canvas = tk.Canvas(
            self.progress_frame,
            bg="#e9ecef",  # Default trough color (will be themed)
            height=6,
            highlightthickness=0,
            relief="flat",
        )
        self.progress_canvas.pack(fill="x", pady=1)  # Center in frame

        # Progress rectangle
        self.progress_rect = self.progress_canvas.create_rectangle(
            0,
            0,
            0,
            10,  # Will be updated
            fill="#02aa20",  # Default progress color (will be themed)
            outline="",  # No outline
            width=0,  # No border
        )

        # Create a progress bar controller object
        self.context.progress_bar = self.ProgressBarController(self)

        # Queue status label BELOW progress bar
        self.context.queue_status_label = tk.Label(
            self.main_frame,
            text="",
            font=self.label_font,
            fg="#007bff",
            anchor="w",
            bg=self.gui_window_bg,
        )
        self.context.queue_status_label.pack(fill="x", padx=30, pady=(2, 1))

        # Button panel with pack
        self.button_panel = tk.Frame(
            self.root, bg=self.gui_window_bg, relief="flat", bd=0
        )
        self.button_panel.pack(fill="both", expand=True, padx=20, pady=(10, 20))

    class ProgressBarController:
        def __init__(self, gui_instance):
            self.gui = gui_instance
            self._progress_value = 0

        @property
        def value(self):
            return self._progress_value

        @value.setter
        def value(self, percent):
            """Update progress (0-100) when value is set"""
            percent = max(0, min(100, percent))  # Clamp to 0-100 range
            self._progress_value = percent

            # Update canvas visualization
            if self.gui.progress_canvas.winfo_width() > 1:
                canvas_width = self.gui.progress_canvas.winfo_width()
                progress_width = (percent / 100) * canvas_width
                self.gui.progress_canvas.coords(
                    self.gui.progress_rect, 0, 0, progress_width, 10
                )

    def create_button_panels(self):
        """Use inner frames with grid inside the pack-managed button_panel"""
        global tk
        # Create a container frame inside button_panel that will use grid
        self.grid_container = tk.Frame(self.button_panel, bg=self.gui_window_bg)
        self.grid_container.pack(fill="both", expand=True)

        self.grid_container.grid_columnconfigure(
            tuple(range(10)), weight=1, uniform="a"
        )
        self.grid_container.grid_rowconfigure(tuple(range(5)), weight=1)

        common_padx = 10
        common_pady = 10

        self.context.buttons = {}  # Initialize buttons dictionary

        # Row 1: Main actions
        self.context.buttons["download_btn"] = ttk.Button(
            self.grid_container,
            text=f"   Video",
            style="Primary.TButton",
            command=lambda: self.on_download_click("video"),
        )
        self.context.buttons["download_btn"].grid(
            row=0,
            column=1,
            columnspan=4,
            padx=common_padx,
            pady=(15, 15),
            sticky="ew",
        )
        self.context.buttons["download_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        self.context.buttons["audio_download_btn"] = ttk.Button(
            self.grid_container,
            text=f"   Audio",
            style="Primary.TButton",
            command=lambda: self.on_download_click("audio"),
        )
        self.context.buttons["audio_download_btn"].grid(
            row=0,
            column=5,
            columnspan=4,
            padx=common_padx,
            pady=(15, 15),
            sticky="ew",
        )
        self.context.buttons["audio_download_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )
        # Row 2: Status buttons
        self.context.buttons["readme_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('readme')} User Guide",
            style="Secondary0.TButton",
            command=lambda: self.context.open_folder("docs_dir"),
        )
        self.context.buttons["readme_btn"].grid(
            row=1,
            column=1,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["readme_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        self.context.buttons["settings_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('settings')} Settings",
            style="Secondary1.TButton",
            command=self.context.open_settings_gui,
        )
        self.context.buttons["settings_btn"].grid(
            row=1,
            column=3,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["settings_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        self.context.buttons["queue_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('queue')} Queue ({self.q_manager.get_queue_count()})",
            style="Secondary2.TButton",
            command=self.context.open_queue_file,
        )
        self.context.buttons["queue_btn"].grid(
            row=1,
            column=5,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["queue_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        self.context.buttons["failed_url_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('error')} Failed ({self.q_manager.get_failed_url_count()})",
            style="Secondary3.TButton",
            command=self.context.open_failed_url_file,
        )
        self.context.buttons["failed_url_btn"].grid(
            row=1,
            column=7,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["failed_url_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        # Row 3: File management buttons
        self.context.buttons["open_download_folder_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('folder')} Downloads",
            style="Secondary4.TButton",
            command=lambda: self.context.open_folder("downloads_dir"),
        )
        self.context.buttons["open_download_folder_btn"].grid(
            row=2,
            column=2,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["open_download_folder_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        self.context.buttons["play_video_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('play')} Play Latest",
            style="Secondary5.TButton",
            command=self.context.play_latest_video,
        )
        self.context.buttons["play_video_btn"].grid(
            row=2,
            column=4,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["play_video_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        self.context.buttons["update_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('refresh')} Update",
            style="Secondary6.TButton",
            # command=self.context.update_tools,
            command=lambda: self.context.update_tools(True),
        )
        self.context.buttons["update_btn"].grid(
            row=2,
            column=6,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["update_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        # Row 4: Control buttons
        self.context.buttons["pause_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('pause')} Pause",
            style="Secondary7.TButton",
            command=self.context.pause_download_callback,
        )
        self.context.buttons["pause_btn"].grid(
            row=3,
            column=1,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["pause_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        self.context.buttons["resume_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('play')} Resume",
            style="Secondary8.TButton",
            command=self.context.resume_download_callback,
        )
        self.context.buttons["resume_btn"].grid(
            row=3,
            column=3,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["resume_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        self.context.buttons["stop_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('stop')} Stop & Del",
            style="Secondary9.TButton",
            command=self.context.stop_download_callback,
        )
        self.context.buttons["stop_btn"].grid(
            row=3,
            column=5,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["stop_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        self.context.buttons["exit_btn"] = ttk.Button(
            self.grid_container,
            text=f"{self.style_manager.get_emoji('exit')} Exit",
            style="Secondary10.TButton",
            command=self.context.exit_app,
        )
        self.context.buttons["exit_btn"].grid(
            row=3,
            column=7,
            columnspan=2,
            padx=common_padx,
            pady=common_pady,
            sticky="ew",
        )
        self.context.buttons["exit_btn"].bind(
            "<Button-1>", lambda e: self.root.after(10, self.root.focus_set)
        )

        # Add some decorative elements
        self.add_decorative_elements()

    def load_icon(self, icon_name, size=(20, 20)):
        """Load icon with transparency support"""
        try:
            assets_dir = Path(self.settings.get("assets_dir", "assets"))
            icon_path = assets_dir / f"{icon_name}.gif"

            icon_path = tk.PhotoImage(file=str(icon_path))
            return icon_path
        except Exception as e:
            print(f"Failed to load icon: {e}")
            return None

    def add_decorative_elements(self):
        """Add some decorative elements for better visual appeal"""
        # Footer with version info
        self.footer = tk.Label(
            self.root,
            text="MediaTools Video Downloader V2.1.0 • © 2025",
            bg=self.gui_window_bg,
            fg="#6c757d",
            font=(self.label_font[0], self.label_font[1] - 3),
        )
        self.footer.place(x=400, y=405, anchor="center")

    import tkinter as tk
    import platform
    import sys

    def setup_bindings(self):
        """Setup event bindings with cross-platform support"""
        # URL entry binding
        self.context.url_entry.bind(
            "<Return>", lambda e: self.context.add_url_to_queue("video")
        )

        # Window close protocol (cross-platform)
        close_protocol = "WM_DELETE_WINDOW"
        if platform.system() == "Darwin":  # macOS
            close_protocol = "WM_DELETE_WINDOW"  # Same on macOS
        elif platform.system() == "Linux":
            close_protocol = "WM_DELETE_WINDOW"  # Same on Linux

        self.root.protocol(close_protocol, self.context.exit_app)

        # Right-click binding
        right_click_button = (
            "<Button-2>" if platform.system() == "Darwin" else "<Button-3>"
        )
        self.context.url_entry.bind(
            right_click_button,
            lambda e: self.right_click(self.root, e, self.context.url_entry),
        )

    def right_click(self, root, event, entry):
        """Hybrid right-click menu – with working X11 grab under VcXsrv/WSL"""
        # 1. Destroy any previous menu
        if getattr(self, "active_menu", None):
            try:
                self.active_menu.destroy()
            except tk.TclError:
                pass
        self.active_menu = None

        # 2. Build the menu (your original code)
        if self.is_wsl():
            menu = tk.Menu(root, tearoff=0, bg="white", fg="black", bd=1)
        else:
            menu = tk.Menu(
                root,
                tearoff=0,
                font=self.label_font,
                bg="#f0f0f0",
                fg="black",
                activebackground="#0078d4",
                activeforeground="white",
                relief="solid",
                bd=1,
            )

        self.active_menu = menu

        for lbl, cmd in (
            ("Cut", lambda: entry.event_generate("<<Cut>>")),
            ("Copy", lambda: entry.event_generate("<<Copy>>")),
            ("Paste", lambda: entry.event_generate("<<Paste>>")),
        ):
            menu.add_command(label=lbl, command=cmd)
        menu.add_separator()
        menu.add_command(
            label="Select All", command=lambda: entry.select_range(0, "end")
        )

        # 3. Show the menu
        menu.tk_popup(event.x_root, event.y_root)

        if self.is_wsl():
            menu.wait_window()

    def is_wsl(self):
        """More robust WSL detection"""
        try:
            # Check multiple indicators
            if platform.system() != "Linux":
                return False

            # Check /proc/version
            try:
                with open("/proc/version", "r") as f:
                    if "microsoft" in f.read().lower():
                        return True
            except Exception:
                pass

            # Check /proc/sys/kernel/osrelease
            try:
                with open("/proc/sys/kernel/osrelease", "r") as f:
                    if "microsoft" in f.read().lower():
                        return True
            except Exception:
                pass

            # Check environment variables
            import os

            if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
                return True

        except Exception:
            pass

        return False

    def on_download_click(self, download_type):
        """Handle download button click"""
        self.context.add_url_to_queue(download_type)
