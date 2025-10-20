import os
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
from mediatools.video.downloader.core.settings_manager import SettingsManager

class QueueManager:
    def __init__(self, style_manager, root):
        self.settings = SettingsManager()
        self.queue_lock = threading.Lock()
        self.style_manager = style_manager
        self.gui_context = None
        self.root = root

        # Initialize file paths from settings
        self._init_file_paths()

        self.previous_session_check_done = False

        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)

        # Initialize files if needed
        if self.multisession_support:
            self._ensure_file_exists(self.queue_file)
            if self.track_failed_url:
                self._ensure_file_exists(self.failed_url_file)

        self._queue_entries = []
        self._failed_entries = []

        # Track file states for quick comparison
        self._queue_file_state = self._get_file_state(self.queue_file)
        self._failed_file_state = self._get_file_state(self.failed_url_file)
        
        self.setup_efficient_monitoring()
    
    def _get_file_state(self, filename):
        """Get current file state (mtime + size)"""
        try:
            stat = os.stat(filename)
            return {'mtime': stat.st_mtime, 'size': stat.st_size}
        except OSError:
            return {'mtime': 0, 'size': 0}
    
    def _is_file_changed(self, filename, last_state):
        """Quick check if file changed using mtime + size"""
        try:
            current_state = self._get_file_state(filename)
            return (current_state['mtime'] != last_state['mtime'] or 
                    current_state['size'] != last_state['size'])
        except OSError:
            return False
    
    def setup_efficient_monitoring(self):
        """Efficient polling using file state checks"""
        def check_files():
            # Check queue file (extremely fast - just stat call)
            if self._is_file_changed(self.queue_file, self._queue_file_state):
                # print("Queue file changed - reloading content")
                self._queue_entries = self._parse_file(self.queue_file)
                self._queue_file_state = self._get_file_state(self.queue_file)
                self.update_button_display()
            
            # Check failed URLs file
            if self._is_file_changed(self.failed_url_file, self._failed_file_state):
                # print("Failed URLs file changed - reloading content")
                self._failed_entries = self._parse_file(self.failed_url_file)
                self._failed_file_state = self._get_file_state(self.failed_url_file)
                self.update_button_display()
            
            # Check again in 4 second
            self.root.after(4000, check_files)
        
        check_files()
    
    def _parse_file(self, filename):
        """Only called when file actually changed"""
        # Your existing file parsing logic here
        entries = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(line)
        except FileNotFoundError:
            pass
        return entries

    def set_gui_context(self, gui_context):
        self.gui_context = gui_context

    def update_button_display(self):
        """Update the queue button and failed url button with current count"""
        self.gui_context.buttons["queue_btn"].config(
            text=f"{self.style_manager.get_emoji('queue')} Queue ({self.get_queue_count()})"
        )
        self.gui_context.buttons["failed_url_btn"].config(
            text=f"{self.style_manager.get_emoji('error')} Failed ({self.get_failed_url_count()})"
        )

    def _init_file_paths(self):
        """Initialize file paths from settings"""
        self.multisession_support = self.settings.get(
            "multisession_queue_download_support", True
        )
        self.track_failed_url = self.settings.get("track_failed_url", True)

        self.data_dir = self.settings.get("data_dir")
        self.queue_file = self.settings.get("queue_file")
        self.queue_file_old = self.settings.get("queue_file_old")
        self.failed_url_file = self.settings.get("failed_url_file")
        self.failed_url_file_old = self.settings.get("failed_url_file_old")

        # Set old file paths
        if self.multisession_support:
            self.queue_old_file = str(Path(self.data_dir) / "queue_old.txt")
            if self.track_failed_url:
                self.failed_url_old_file = str(
                    Path(self.data_dir) / "failed_url_old.txt"
                )

    def _ensure_file_exists(self, filepath):
        """Create file if it doesn't exist"""
        if filepath and not os.path.exists(filepath):
            open(filepath, "w", encoding="utf-8").close()

    def _read_file_lines(self, filepath):
        """Read all lines from file, return empty list if file doesn't exist"""
        if not filepath or not os.path.exists(filepath):
            return []
        try:
            self.check_file_entries(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return []

    def check_file_entries(self, filepath):
        """Check for white spaces or missing newline in last line"""
        if not filepath or not os.path.exists(filepath):
            return
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
                if not content.strip():  # Empty file
                    return
                    
                lines = [line.strip() for line in content.splitlines() if line.strip()]
                if not lines:
                    return
                    
                update_file = False
                new_lines = []
                
                content_without_newline = content.replace('\n', '_')
                # Check 1: If file has whitespace-separated entries (not line-by-line)
                if any(c.isspace() for c in content_without_newline) or ',' in content_without_newline:
                    # print(f"Found whitespace-or comma separated entries in {filepath}, normalizing...")
                    # Process content to treat whitespaces as separators
                    entries = re.split(r'[,\s]+', content)
                    entries = [entry.strip() for entry in entries if entry.strip()]
                    new_lines = entries
                    update_file = True
                    
                # Check 2: If last line doesn't end with newline
                elif not content.endswith('\n'):
                    # print(f"Last line missing newline in {filepath}, fixing...")
                    new_lines = lines
                    update_file = True
                    
                else:
                    # File is already in good format
                    return
                
            if update_file:
                with open(filepath, "w", encoding="utf-8") as f:
                    for line in new_lines:
                        f.write(f"{line}\n")
                # print(f"Normalized {len(new_lines)} entries in {filepath}")
            
        except Exception as e:
            print(f"Error checking entries in {filepath}: {e}")

    def _write_file_lines(self, filepath, lines):
        """Write lines to file"""
        if not filepath:
            return
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(f"{line}\n")
        except Exception as e:
            print(f"Error writing to {filepath}: {e}")

    def _append_to_file(self, filepath, line_s):
        """Append a line or lines to file, avoiding duplicates"""
        if not filepath:
            return

        existing_lines = set()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    existing_lines.add(line.strip())
        except Exception as e:
            print(f"Error reading file for duplicate check: {e}")
            return

        try:
            with open(filepath, "a", encoding="utf-8") as f:
                if isinstance(line_s, list):
                    for line in line_s:
                        normalized_line = line.strip()
                        if normalized_line and normalized_line not in existing_lines:
                            f.write(f"{normalized_line}\n")
                else:
                    normalized_line = line_s.strip()
                    if normalized_line and normalized_line not in existing_lines:
                        f.write(f"{normalized_line}\n")
        except Exception as e:
            print(f"Error appending to {filepath}: {e}")

    def _move_to_old_file(self, source_file, old_file):
        """Move contents of source file to old file"""

        if not source_file or not old_file:
            return

        source_lines = self._read_file_lines(source_file)
        if source_lines:
            try:
                with open(old_file, "a", encoding="utf-8") as f:
                    for line in source_lines:
                        f.write(f"{line}\n")
                # Clear the source file
                open(source_file, "w").close()
            except Exception as e:
                print(f"Error moving {source_file} to {old_file}: {e}")

    def check_previous_session(self, root):
        """Check for previous session files and prompt user"""

        # Handle old files from previous sessions
        if os.path.exists(self.queue_file_old):
            queue_urls_old = self._read_file_lines(self.queue_file_old)
            self._append_to_file(self.queue_file, queue_urls_old)
            os.remove(self.queue_file_old)

        if self.track_failed_url and os.path.exists(self.failed_url_file_old):
            failed_urls_old = self._read_file_lines(self.failed_url_file_old)
            self._append_to_file(self.failed_url_file, failed_urls_old)
            os.remove(self.failed_url_file_old)

        if not self.multisession_support:
            queue_urls = self._read_file_lines(self.queue_file)
            (
                Path(self.queue_file_old).touch()
                if not Path(self.queue_file_old).exists()
                else None
            )
            self._append_to_file(self.queue_file_old, queue_urls)
            open(self.queue_file, "w", encoding="utf-8").close()

            failed_urls = self._read_file_lines(self.failed_url_file)
            (
                Path(self.failed_url_file_old).touch()
                if not Path(self.failed_url_file_old).exists()
                else None
            )
            self._append_to_file(self.failed_url_file_old, failed_urls)
            open(self.failed_url_file, "w", encoding="utf-8").close()

            return

        queue_urls = self._read_file_lines(self.queue_file)
        failed_urls = (
            self._read_file_lines(self.failed_url_file) if self.track_failed_url else []
        )

        if not queue_urls and not failed_urls:
            return

        # Show dialog to user
        self._show_session_dialog(root, queue_urls, failed_urls)

    def _show_session_dialog(self, root, queue_urls, failed_urls):
        """Show dialog for previous session handling"""
        message_parts = []
        if queue_urls:
            message_parts.append(f"• {len(queue_urls)} pending URLs in queue")
        if failed_urls:
            message_parts.append(
                f"• {len(failed_urls)} failed URLs from previous sessions"
            )

        message = "Previous session data found:\n\n" + "\n".join(message_parts)
        message += "\n\nWhat would you like to do?"

        dialog = PreviousSessionDialog(
            root, message, queue_urls, failed_urls, self.style_manager
        )
        choice = dialog.result

        if choice == "delete":
            self._clear_all_files()
        elif choice == "ignore":
            self._move_to_old_files()
        elif choice == "continue":
            # self._continue_previous_session(queue_urls, failed_urls)
            self._continue_previous_session()

        self.previous_session_check_done = True

    def _continue_previous_session(self):
        failed_urls = self._read_file_lines(self.failed_url_file)
        self._append_to_file(self.queue_file, failed_urls)
        open(self.failed_url_file, "w").close()

    def _clear_all_files(self):
        """Clear all queue and failed URL files"""
        if self.queue_file:
            open(self.queue_file, "w").close()
        if self.failed_url_file:
            open(self.failed_url_file, "w").close()

    def _move_to_old_files(self):
        """Move current files to old files"""
        if self.multisession_support:
            self._move_to_old_file(self.queue_file, self.queue_old_file)
            if self.track_failed_url:
                self._move_to_old_file(self.failed_url_file, self.failed_url_old_file)

    def add_url(self, url):
        """Add URL to queue (thread-safe)"""
        if not url.strip():
            return False

        url = url.strip()

        with self.queue_lock:
            self._append_to_file(self.queue_file, url)
        return True

    def get_next_url(self):
        """Get next URL from queue (thread-safe)"""
        with self.queue_lock:
            urls = self._read_file_lines(self.queue_file)
            return urls[0] if urls else None

    def remove_url(self, url=None):
        """Remove URL from queue (thread-safe)"""
        with self.queue_lock:
            urls = self._read_file_lines(self.queue_file)
            if urls:
                if url:
                    # Remove specific URL
                    urls = [u for u in urls if u != url]
                else:
                    # Remove first URL
                    urls = urls[1:]
                self._write_file_lines(self.queue_file, urls)

    def get_queue_count(self):
        """Get number of URLs in queue (thread-safe)"""
        with self.queue_lock:
            return len(self._read_file_lines(self.queue_file))

    def get_failed_url_count(self):
        """Get number of URLs in queue (thread-safe)"""
        with self.queue_lock:
            return len(self._read_file_lines(self.failed_url_file))

    def has_queued_urls(self):
        """Check if there are URLs in queue"""
        return self.get_queue_count() > 0

    def add_failed_url(self, url, error_message=""):
        """Add URL to failed list"""
        if not self.track_failed_url:
            return

        failed_entry = url  # Simplified - can add timestamp/error if needed

        with self.queue_lock:
            if self.multisession_support:
                self._append_to_file(self.failed_url_file, failed_entry)

    def cleanup(self):
        """Clean up on exit"""
        if not self.multisession_support:
            pass

    def get_all_queued_urls(self):
        """Get all URLs in queue"""
        with self.queue_lock:
            return self._read_file_lines(self.queue_file)


    def get_previous_session_check_done(self):
        """Previous session check done"""
        return self.previous_session_check_done

class PreviousSessionDialog:
    """Custom dialog for previous session options (cross-platform safe)"""

    def __init__(self, parent, message, queue_urls, failed_urls, style_manager):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Previous Session Found")
        self.dialog.resizable(False, False)
        parent.update_idletasks()
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Set fixed size and center relative to parent
        w, h = 500, 320
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w // 2) - (w // 2)
        y = parent_y + (parent_h // 2) - (h // 2)
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

        # Fonts from style manager (with fallback)
        try:
            font_config = style_manager.get_font_config("button")
            self.button_font = (font_config["family"], font_config["size"])
        except Exception:
            self.button_font = ("Arial", 9)

        try:
            font_config = style_manager.get_font_config("label")
            self.label_font = (font_config["family"], font_config["size"])
        except Exception:
            self.label_font = ("Arial", 10)

        # Button colors for hover effects
        self.button_colors = {
            "delete": {
                "active_bg": "#ff5252",
                "fg": "black",
                "bg": "#ff6b6b",
                "active_fg": "black",
            },
            "ignore": {
                "active_bg": "#feca57",
                "fg": "black",
                "bg": "#ffd77a",
                "active_fg": "black",
            },
            "continue": {
                "active_bg": "#48dbfb",
                "fg": "black",
                "bg": "#6ee4ff",
                "active_fg": "black",
            },
        }

        # Create UI
        self._create_widgets(message, queue_urls, failed_urls)

        # Handle close (X button) → default to ignore
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_result("ignore"))

        # Keyboard shortcuts
        self.dialog.bind("<Escape>", lambda e: self._set_result("ignore"))
        self.dialog.bind(
            "<Return>", lambda e: self.btn1.invoke()
        )  # Enter triggers first button

        # Wait for user choice
        parent.wait_window(self.dialog)

    def _create_widgets(self, message, queue_urls, failed_urls):
        """Create all widgets for the dialog"""

        # Message frame
        msg_frame = tk.Frame(self.dialog)
        msg_frame.pack(fill=tk.X, padx=20, pady=20)

        msg_label = tk.Label(
            msg_frame,
            text=message,
            justify=tk.LEFT,
            wraplength=460,  # safe fixed wrap
            font=self.label_font,
        )
        msg_label.pack(anchor=tk.W)

        # Buttons frame
        btn_frame = tk.Frame(self.dialog)
        btn_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        btn_frame.columnconfigure(0, weight=1)

        # Buttons
        self.btn1 = tk.Button(
            btn_frame,
            text="Delete All Previous Data",
            command=lambda: self._set_result("delete"),
            bg=self.button_colors["delete"]["bg"],
            fg=self.button_colors["delete"]["fg"],
            font=self.button_font,
            width=25,
            height=2,
            relief=tk.RAISED,
            borderwidth=1,
        )
        self.btn1.grid(row=0, column=0, sticky="ew", pady=5)
        self._bind_hover_effects(self.btn1, "delete")

        self.btn2 = tk.Button(
            btn_frame,
            text="Ignore For This Session",
            command=lambda: self._set_result("ignore"),
            bg=self.button_colors["ignore"]["bg"],
            fg=self.button_colors["ignore"]["fg"],
            font=self.button_font,
            width=25,
            height=2,
            relief=tk.RAISED,
            borderwidth=1,
        )
        self.btn2.grid(row=1, column=0, sticky="ew", pady=5)
        self._bind_hover_effects(self.btn2, "ignore")

        self.btn3 = tk.Button(
            btn_frame,
            text="Continue Previous Downloads",
            command=lambda: self._set_result("continue"),
            bg=self.button_colors["continue"]["bg"],
            fg=self.button_colors["continue"]["fg"],
            font=self.button_font,
            width=25,
            height=2,
            relief=tk.RAISED,
            borderwidth=1,
        )
        self.btn3.grid(row=2, column=0, sticky="ew", pady=5)
        self._bind_hover_effects(self.btn3, "continue")

        # Set initial keyboard focus
        self.btn1.focus_set()

    def _set_result(self, choice):
        self.result = choice
        self.dialog.destroy()

    def _bind_hover_effects(self, button, button_type):
        """Bind hover effects to button"""
        colors = self.button_colors[button_type]

        def on_enter(e):
            button.config(
                bg=colors["active_bg"], fg=colors["active_fg"], cursor="hand2"
            )

        def on_leave(e):
            button.config(bg=colors["bg"], fg=colors["fg"], cursor="")

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
