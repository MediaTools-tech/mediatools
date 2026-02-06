import os
import sys
import platform
import subprocess
import logging
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from mediatools.video.transcoder import __version__


class ShortcutCreator:
    def __init__(self, settings_manager=None):
        self.app_name = f"MediaTools Video Transcoder v{__version__}"
        self.exe_name = "mt-vtc.exe"
        self.settings_manager = settings_manager
        self.logger = logging.getLogger(__name__)

        # Check Windows dependencies once at initialization
        self._check_windows_dependencies()

    def _check_windows_dependencies(self):
        """Check for Windows dependencies at initialization"""
        self.has_windows_deps = False
        if platform.system() == "Windows":
            try:
                import winshell
                from win32com.client import Dispatch

                self.has_windows_deps = True
                self.logger.info("Windows shortcut dependencies available")
            except ImportError:
                self.logger.info(
                    "Windows shortcut dependencies not available, using fallback methods"
                )

    def create_desktop_shortcut_cross_platform(self):
        """Cross-platform desktop shortcut creation"""
        system = platform.system()
        self.logger.info(f"Creating desktop shortcut for {system}")

        try:
            if system == "Windows":
                return self._create_windows_shortcut()
            elif system == "Darwin":
                return self._create_mac_shortcut()
            elif system == "Linux":
                return self._create_linux_shortcut()
            else:
                messagebox.showwarning(
                    "Unsupported Platform",
                    f"Shortcut creation not supported on {system}",
                )
                return False
        except Exception as e:
            self.logger.error(f"Shortcut creation failed: {e}")
            messagebox.showerror("Error", f"Could not create shortcut: {e}")
            return False

    def _find_project_root(self, current_path):
        """Find the project root by looking for common markers"""
        current = Path(current_path).absolute()

        markers = [
            "src",
            "setup.py",
        ]

        # Go up directories until we find a project root marker
        for parent in [current] + list(current.parents):
            for marker in markers:
                if (parent / marker).exists():
                    return parent

        return current

    def _get_executable_and_icon_paths(self):
        """Get executable path and platform-appropriate icon path"""
        if getattr(sys, "frozen", False):
            # PyInstaller executable
            exe_path = sys.executable
            assets_dir = Path(self.settings_manager.get("assets_dir", "assets"))

            system = platform.system()
            if system == "Windows":
                icon_path = assets_dir / "Logo_128x128.ico"
            elif system == "Darwin":
                icon_path = assets_dir / "Logo_128x128.icns"
            else:  # Linux
                icon_path = assets_dir / "Logo_128x128.png"
        else:
            # Development mode
            exe_path = Path(sys.argv[0]).absolute()
            project_root = self._find_project_root(exe_path)

            possible_asset_dirs = [
                project_root / "src" / "mediatools" / "video" / "transcoder" / "assets",
                project_root / "assets",
            ]

            assets_dir = None
            for asset_dir in possible_asset_dirs:
                if asset_dir.exists():
                    assets_dir = asset_dir
                    break

            if not assets_dir:
                assets_dir = project_root

            system = platform.system()
            if system == "Windows":
                icon_path = assets_dir / "Logo_128x128.ico"
            elif system == "Darwin":
                icon_path = assets_dir / "Logo_128x128.icns"
            else:  # Linux
                icon_path = assets_dir / "Logo_128x128.png"

        return str(exe_path), icon_path

    def _create_windows_shortcut(self):
        """Windows shortcut creation"""
        if self.has_windows_deps:
            return self._create_windows_proper_shortcut()
        else:
            return self._create_windows_manual_shortcut()

    def _create_windows_proper_shortcut(self):
        """Create proper Windows .lnk shortcut"""
        try:
            import winshell
            from win32com.client import Dispatch

            try:
                desktop = winshell.desktop()
            except:
                desktop = str(Path.home() / "Desktop")

            shortcut_path = Path(desktop) / f"{self.app_name}.lnk"
            exe_path, icon_path = self._get_executable_and_icon_paths()

            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))

            shortcut.Targetpath = str(exe_path)
            shortcut.WorkingDirectory = str(Path(exe_path).parent)
            shortcut.Description = f"{self.app_name} - High-quality video transcoding"

            if icon_path and icon_path.exists():
                shortcut.IconLocation = f"{str(icon_path)},0"
            else:
                shortcut.IconLocation = f"{str(exe_path)},0"

            shortcut.save()
            messagebox.showinfo("Success", "Desktop shortcut created!")
            return True

        except Exception as e:
            self.logger.error(f"Proper Windows shortcut failed: {e}")
            return self._create_windows_manual_shortcut()

    def _create_windows_manual_shortcut(self):
        """Manual Windows shortcut using batch file"""
        try:
            desktop = Path.home() / "Desktop"
            exe_path, _ = self._get_executable_and_icon_paths()

            bat_content = f"""@echo off
cd /d "{Path(exe_path).parent}"
start "" "{Path(exe_path).name}"
"""
            bat_path = desktop / f"{self.app_name}.bat"
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)

            messagebox.showinfo("Success", "Desktop shortcut created as batch file!")
            return True
        except Exception as e:
            self.logger.error(f"Manual Windows shortcut failed: {e}")
            return False

    def _create_linux_shortcut(self):
        """Linux .desktop file creation"""
        try:
            desktop = Path.home() / "Desktop"
            desktop_file = (
                desktop / f"{self.app_name.replace(' ', '-').lower()}.desktop"
            )

            exe_path, icon_path = self._get_executable_and_icon_paths()

            desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={self.app_name}
Comment=High-quality video transcoding
Exec="{exe_path}"
Path={Path(exe_path).parent}
Icon={icon_path if icon_path.exists() else ""}
Terminal=false
StartupNotify=true
Categories=AudioVideo;Video;
"""
            with open(desktop_file, "w", encoding="utf-8") as f:
                f.write(desktop_content)

            os.chmod(desktop_file, 0o755)
            messagebox.showinfo("Success", "Desktop shortcut created!")
            return True
        except Exception as e:
            self.logger.error(f"Linux shortcut failed: {e}")
            return False

    def _create_mac_shortcut(self):
        """macOS shortcut creation"""
        try:
            desktop = Path.home() / "Desktop"
            exe_path, icon_path = self._get_executable_and_icon_paths()

            script_content = f"""#!/bin/bash
cd "{Path(exe_path).parent}"
./"{Path(exe_path).name}"
"""
            script_path = desktop / f"{self.app_name}.command"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)

            messagebox.showinfo("Success", "Desktop shortcut created!")
            return True
        except Exception as e:
            self.logger.error(f"macOS shortcut failed: {e}")
            return False

    def shortcut_exists(self):
        """Check if shortcut already exists on desktop"""
        desktop = Path.home() / "Desktop"
        system = platform.system()

        if system == "Windows":
            return (desktop / f"{self.app_name}.lnk").exists() or (
                desktop / f"{self.app_name}.bat"
            ).exists()
        elif system == "Darwin":
            return (desktop / f"{self.app_name}.command").exists()
        elif system == "Linux":
            return (
                desktop / f"{self.app_name.replace(' ', '-').lower()}.desktop"
            ).exists()
        return False

    def first_run_setup(self):
        """Check if first run and offer shortcut creation"""
        if self.shortcut_exists():
            return

        if self.settings_manager:
            data_dir = Path(self.settings_manager.get("data_dir", Path.home() / ".mediatools"))
        else:
            data_dir = Path.home() / ".mediatools"

        first_run_file = data_dir / "transcoder_first_run.flag"

        if not first_run_file.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            
            response = messagebox.askyesno(
                "Create Desktop Shortcut",
                f"Would you like to create a desktop shortcut for {self.app_name}?",
            )
            if response:
                self.create_desktop_shortcut_cross_platform()

            try:
                first_run_file.touch()
            except Exception as e:
                self.logger.warning(f"Could not create first run flag: {e}")
