import platform
import tkinter as tk
from tkinter import font as tkfont, messagebox, ttk
import sys
import os


class PlatformStyleManager:
    """
    Cross-platform compatible style manager for fonts, emojis, and UI elements
    Handles font detection and emoji compatibility across Windows, Linux, macOS, and WSL
    """

    def __init__(self, ttk_style=None):
        self.system = platform.system().lower()
        self.is_wsl = self._detect_wsl()

        # Initialize tkinter root for font detection
        self._root = tk.Tk()
        self._root.withdraw()  # Hide the window

        # Store reference to ttk.Style for font configuration
        self.ttk_style = ttk_style or ttk.Style()

        # Platform-specific font preferences (ordered by preference)
        self.font_preferences = {
            "windows": [
                "Segoe UI",
                "Segoe UI Symbol",
                "Segoe UI Emoji",
                "Arial",
                "Helvetica",
                "Calibri",
                "Tahoma",
            ],
            "linux": [
                "Ubuntu",
                "DejaVu Sans",
                "Liberation Sans",
                "Noto Sans",
                "Arial",
                "Helvetica",
                "sans-serif",
            ],
            "darwin": [  # macOS
                "San Francisco",
                "Helvetica Neue",
                "Arial",
                "Lucida Grande",
                "Geneva",
                "Verdana",
            ],
            "wsl": [
                "Ubuntu",
                "DejaVu Sans",
                "Liberation Sans",
                "Arial",
                "Helvetica",
                "sans-serif",
            ],
        }

        # Emoji compatibility by platform
        self.emoji_sets = {
            "full": {
                "settings": "⚙️",
                "play": "▶️",
                "pause": "⏸️",
                "stop": "⏹️",
                "download": "⬇️",
                "folder": "📁",
                "file": "📄",
                "success": "✅",
                "error": "❌",
                "warning": "⚠️",
                "info": "ℹ️",
                "loading": "⏳",
                "queue": "📋",
                "trash": "🗑️",
                "refresh": "🔄",
                "readme": "📖",
                "exit": "🚪",
                "find": "🔍",
                "question": "?",
                "yesno": "?",
                "check": "✓",
            },
            "basic": {
                "settings": "⚙",
                "play": "▶",
                "pause": "||",
                "stop": "x",
                "download": "↓",
                "folder": "↓",
                "file": "",
                "success": "✓",
                "error": "✗",
                "warning": "!",
                "info": "[i]",
                "loading": "↻",
                "queue": "≡",
                "trash": "[x]",
                "refresh": "↻",
                "readme": "≡",
                "exit": "|X|",
                "find": "",
                "question": "?",
                "yesno": "?",
                "check": "✓",
            },
            "text": {
                "settings": "⚙",
                "play": "▶",
                "pause": "||",
                "stop": "⏹",
                "download": "↓",
                "folder": "📁",
                "file": "",
                "success": "✓",
                "error": "✗",
                "warning": "!",
                "info": "[i]",
                "loading": "↻",
                "queue": "≡",
                "trash": "[x]",
                "refresh": "↻",
                "readme": "",
                "exit": "X",
                "find": "",
                "question": "?",
                "yesno": "?",
                "check": "✓",
            },
        }

        # Initialize platform-specific settings
        self.selected_font = self._detect_best_font()
        self.emoji_set = self._detect_emoji_compatibility()

        # Font sizes by component type
        self.font_sizes = {
            "default": 9 if self.system == "windows" else 10,
            "button": 10 if self.system == "windows" else 10,
            "label": 9 if self.system == "windows" else 10,
            "title": 12 if self.system == "windows" else 13,
            "messagebox": 10 if self.system == "windows" else 10,
        }

        # Configure ttk styles with detected fonts (after font_sizes is set)
        self._configure_ttk_styles()

        try:
            font_config = self.get_font_config("label")
            self.label_font = (font_config["family"], font_config["size"])
        except Exception:
            self.label_font = ("Arial", 10)

    def _detect_wsl(self):
        """Detect if running under WSL"""
        try:
            if "microsoft" in platform.release().lower():
                return True
            if os.path.exists("/proc/version"):
                with open("/proc/version", "r") as f:
                    if "microsoft" in f.read().lower():
                        return True
        except:
            pass
        return False

    def _detect_best_font(self):
        """Detect the best available font for the current platform"""
        platform_key = "wsl" if self.is_wsl else self.system
        preferred_fonts = self.font_preferences.get(
            platform_key, self.font_preferences["linux"]
        )

        # Get all available system fonts
        available_fonts = set(tkfont.families())

        # Find the first available preferred font
        for font_name in preferred_fonts:
            if font_name in available_fonts:
                return font_name

        # Fallback to system default
        return "TkDefaultFont"

    def _test_emoji_display(self, emoji_text):
        """Test if an emoji displays correctly"""
        try:
            # Create a temporary label to test emoji rendering
            test_label = tk.Label(self._root, text=emoji_text)
            test_label.update()

            # Basic heuristic: if the font can measure the emoji, it might work
            font_obj = tkfont.Font(family=self.selected_font)
            width = font_obj.measure(emoji_text)

            test_label.destroy()
            return width > 0
        except:
            return False

    def _detect_emoji_compatibility(self):
        """Detect which emoji set works best on the current platform"""
        # For WSL, even if emojis might render in GUI, terminal support is limited
        if self.is_wsl:
            # WSL terminals typically have poor emoji support
            return "basic"

        # Test a few key emojis
        test_emojis = ["⚙️", "▶️", "⬇️"]

        # For basic Linux without proper emoji fonts
        if self.system == "linux" and "ubuntu" not in platform.version().lower():
            working_emojis = 0
            for emoji in test_emojis:
                if self._test_emoji_display(emoji):
                    working_emojis += 1

            if working_emojis >= 2:  # At least 2 out of 3 work
                return "full"
            else:
                # return "basic" if working_emojis >= 1 else "text"
                return "basic"

        # For Windows and macOS, try full set first
        elif self.system in ["windows", "darwin"]:
            return "full"

        # For Linux with Ubuntu, try basic first
        elif self.system == "linux":
            return "basic"

        # Default to text for unknown systems
        else:
            return "text"

    def _configure_ttk_styles(self):
        """Configure ttk styles with platform-appropriate fonts"""
        button_font = self.get_font_config("button")
        label_font = self.get_font_config("label")

        # Configure existing button styles
        button_styles = [
            "TButton",
            "Secondary6.TButton",
            "Accent.TButton",
            "Primary.TButton",
            "Secondary.TButton",
        ]

        for style_name in button_styles:
            try:
                self.ttk_style.configure(
                    style_name, font=(button_font["family"], button_font["size"])
                )
            except tk.TclError:
                # Style might not exist yet, that's okay
                pass

        # Configure label styles
        label_styles = ["TLabel", "Heading.TLabel", "Title.TLabel"]

        for style_name in label_styles:
            try:
                self.ttk_style.configure(
                    style_name, font=(label_font["family"], label_font["size"])
                )
            except tk.TclError:
                pass

    def configure_ttk_widget_style(self, style_name, component_type="button"):
        """Configure a specific ttk style with appropriate font"""
        font_config = self.get_font_config(component_type)
        try:
            self.ttk_style.configure(
                style_name, font=(font_config["family"], font_config["size"])
            )
        except tk.TclError as e:
            print(f"Warning: Could not configure style {style_name}: {e}")

    def create_ttk_button(
        self, parent, text, emoji_name=None, style="TButton", **kwargs
    ):
        """Create a ttk.Button with proper font and emoji configuration"""
        button_text = self.get_button_text(text, emoji_name) if emoji_name else text

        # Ensure the style has proper font configuration
        self.configure_ttk_widget_style(style, "button")

        return ttk.Button(parent, text=button_text, style=style, **kwargs)

    def create_ttk_label(self, parent, text, emoji_name=None, style="TLabel", **kwargs):
        """Create a ttk.Label with proper font and emoji configuration"""
        label_text = f"{self.get_emoji(emoji_name)} {text}" if emoji_name else text

        # Ensure the style has proper font configuration
        self.configure_ttk_widget_style(style, "label")

        return ttk.Label(parent, text=label_text, style=style, **kwargs)

    def get_font_config(self, component_type="default"):
        """Get font configuration for a specific component type"""
        size = self.font_sizes.get(component_type, self.font_sizes["default"])
        return {"family": self.selected_font, "size": size}

    def get_emoji(self, emoji_name):
        """Get platform-appropriate emoji"""
        return self.emoji_sets[self.emoji_set].get(emoji_name, f"[{emoji_name}]")

    def get_button_text(self, base_text, emoji_name=None):
        """Get button text with appropriate emoji"""
        if emoji_name:
            emoji = self.get_emoji(emoji_name)
            return f"{emoji} {base_text}"
        return base_text

    def get_platform_info(self):
        """Get detailed platform information for debugging"""
        return {
            "system": self.system,
            "is_wsl": self.is_wsl,
            "selected_font": self.selected_font,
            "emoji_set": self.emoji_set,
            "platform_release": platform.release(),
            "available_fonts_count": len(tkfont.families()),
            "python_version": sys.version,
        }

    def print_debug_info(self):
        """Print debug information about platform detection"""
        info = self.get_platform_info()
        print("=== Platform Style Manager Debug Info ===")
        for key, value in info.items():
            print(f"{key}: {value}")

        print("\nEmoji Test:")
        test_emojis = ["settings", "play", "download", "success", "error"]
        for emoji_name in test_emojis:
            emoji = self.get_emoji(emoji_name)
            print(f"{emoji_name}: {emoji}")

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, "_root") and self._root:
            self._root.destroy()
