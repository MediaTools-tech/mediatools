import tkinter as tk
from tkinter import ttk
from mediatools.video.downloader.compat.platform_style_manager import PlatformStyleManager


class CustomMessageBoxCore:
    def __init__(
        self,
        parent,
        title,
        message,
        msg_type="info",
        font=("Arial", 9),
        yes="Yes",
        no="No",
        emoji=None,
    ):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x160")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.style_manager = PlatformStyleManager()

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

        # Configure background
        bg_color = "#f0f0f0"
        self.dialog.configure(bg=bg_color)

        # Center dialog
        self._center_dialog(parent)

        # Main frame
        main_frame = tk.Frame(self.dialog, bg=bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Icon and message frame
        content_frame = tk.Frame(main_frame, bg=bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Add icon based on message type
        icon_text = self._get_icon(emoji) if emoji else self._get_icon(msg_type)
        if icon_text:
            icon_label = tk.Label(
                content_frame,
                text=icon_text,
                font=(self.messagebox_font[0], self.messagebox_font[1] + 5),
                bg=bg_color,
                fg=(
                    self._get_icon_color(emoji)
                    if emoji
                    else self._get_icon_color(msg_type)
                ),
            )
            icon_label.pack(side=tk.LEFT, padx=(0, 10))

        # Message
        msg_label = tk.Label(
            content_frame,
            text=message,
            font=self.label_font,
            bg=bg_color,
            fg="#000000",
            wraplength=300,
            justify=tk.LEFT,
        )
        msg_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = tk.Frame(main_frame, bg=bg_color)
        btn_frame.pack(fill=tk.X)

        if msg_type == "yesno":
            self._create_yesno_buttons(btn_frame, font, bg_color, yes, no)
        else:
            self._create_ok_button(btn_frame, font, bg_color)

        # Wait for result
        parent.wait_window(self.dialog)

    def _center_dialog(self, parent):
        """Center dialog on parent"""
        self.dialog.update_idletasks()
        x = (
            parent.winfo_rootx()
            + (parent.winfo_width() // 2)
            - (self.dialog.winfo_width() // 2)
        )
        y = (
            parent.winfo_rooty()
            + (parent.winfo_height() // 2)
            - (self.dialog.winfo_height() // 2)
        )
        self.dialog.geometry(f"+{x}+{y}")

    def _get_icon(self, msg_type):
        """Get icon character for message type"""
        return self.style_manager.get_emoji(msg_type)

    def _get_icon_color(self, msg_type):
        """Get color for icon"""
        colors = {
            "info": "#0078d4",
            "warning": "#ff8c00",
            "error": "#dc3545",
            "question": "#0078d4",
            "yesno": "#0078d4",
        }
        return colors.get(msg_type, "#000000")

    def _create_ok_button(self, parent, font, bg_color):
        """Create OK button"""
        btn = tk.Button(
            parent,
            text="OK",
            command=self._ok_clicked,
            font=self.button_font,
            width=10,
            bg="#e0e0e0",
            relief="raised",
            bd=1,
        )
        btn.pack(side=tk.RIGHT)
        btn.focus_set()

        # Bind Enter key
        self.dialog.bind("<Return>", lambda e: self._ok_clicked())
        self.dialog.bind("<Escape>", lambda e: self._ok_clicked())

    def _create_yesno_buttons(self, parent, font, bg_color, yes, no):
        """Create Yes/No buttons"""
        no_btn = tk.Button(
            parent,
            text=no,
            command=self._no_clicked,
            font=self.button_font,
            width=10,
            bg="#e0e0e0",
            relief="raised",
            bd=1,
        )
        no_btn.pack(side=tk.RIGHT, padx=(5, 0))

        yes_btn = tk.Button(
            parent,
            text=yes,
            command=self._yes_clicked,
            font=self.button_font,
            width=10,
            bg="#007bff",
            fg="white",
            relief="raised",
            bd=1,
        )
        yes_btn.pack(side=tk.RIGHT)
        yes_btn.focus_set()

        # Bind keys
        self.dialog.bind("<Return>", lambda e: self._yes_clicked())
        self.dialog.bind("<Escape>", lambda e: self._no_clicked())

    def _ok_clicked(self):
        self.result = True
        self.dialog.destroy()

    def _yes_clicked(self):
        self.result = True
        self.dialog.destroy()

    def _no_clicked(self):
        self.result = False
        self.dialog.destroy()


class CustomMessageBox:
    def __init__(self):
        pass

    # Wrapper functions to replace messagebox calls
    def custom_showinfo(self, parent, title, message, font=("Arial", 9)):
        """custom_showinfo"""
        dialog = CustomMessageBoxCore(parent, title, message, "info", font)
        return dialog.result

    def custom_showerror(self, parent, title, message, font=("Arial", 9)):
        dialog = CustomMessageBoxCore(parent, title, message, "error", font)
        return dialog.result

    def custom_showwarning(self, parent, title, message, font=("Arial", 9)):
        dialog = CustomMessageBoxCore(parent, title, message, "warning", font)
        return dialog.result

    def custom_askyesno(
        self, parent, title, message, font=("Arial", 9), yes="Yes", no="No", emoji=None
    ):
        dialog = CustomMessageBoxCore(
            parent, title, message, "yesno", font, yes, no, emoji
        )
        return dialog.result
