import os
import sys
import platform
import subprocess
import logging
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from mediatools.video.downloader import __version__


class ShortcutCreator:
    def __init__(self, settings_manager=None):
        # self.app_name = "MediaTools Video Downloader"
        self.app_name = f"MediaTools Video Downloader v{__version__}"
        self.exe_name = "mt-vdl.exe"
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

    def _find_assets_directory(self, current_path):
        """Safely find assets directory without hardcoded assumptions"""
        possible_paths = [
            current_path.parent / "assets",
            current_path.parent / "src" / "video" / "downloader" / "assets",
            current_path.parent.parent / "assets",
            current_path.parent / "src" / "assets",
            current_path / "assets",  # Current directory
        ]

        for path in possible_paths:
            if path.exists():
                self.logger.info(f"Found assets directory: {path}")
                return path

        self.logger.warning("Assets directory not found, using executable directory")
        return current_path.parent  # Fallback

    def _find_project_root(self, current_path):
        """Find the project root by looking for common markers"""
        current = Path(current_path).absolute()

        # Look for project root markers
        # markers = [
        #     "src",
        #     "assets",
        #     "requirements.txt",
        #     "pyproject.toml",
        #     ".git",
        #     "README.md",
        #     "setup.py",
        # ]

        markers = [
            "src",
            "setup.py",
        ]

        # Go up directories until we find a project root marker
        for parent in [current] + list(current.parents):
            for marker in markers:
                if (parent / marker).exists():
                    self.logger.info(f"Found project root: {parent} (marker: {marker})")
                    return parent

        self.logger.warning(f"Project root not found, using: {current}")
        return current

    def _get_executable_and_icon_paths(self):
        """Get executable path and platform-appropriate icon path"""
        if getattr(sys, "frozen", False):
            # PyInstaller executable
            exe_path = sys.executable

            assets_dir = Path(self.settings_manager.get("assets_dir", "assets"))

            # Platform-specific icon paths
            system = platform.system()
            if system == "Windows":
                icon_path = assets_dir / "icon.ico"
            elif system == "Darwin":
                icon_path = assets_dir / "icon.icns"
            else:  # Linux
                icon_path = assets_dir / "icon.png"
        else:
            # Development mode - dynamically find assets
            exe_path = Path(sys.argv[0]).absolute()
            project_root = self._find_project_root(exe_path)

            possible_asset_dirs = [
                project_root / "src" / "mediatools" / "video" / "downloader" / "assets",
                project_root / "assets",
                project_root / "src" / "assets",
                project_root / "resources",
            ]

            assets_dir = None
            for asset_dir in possible_asset_dirs:
                if asset_dir.exists():
                    assets_dir = asset_dir
                    self.logger.info(f"Found assets directory: {assets_dir}")
                    break

            if not assets_dir:
                self.logger.warning("No assets directory found, using project root")
                assets_dir = project_root

            system = platform.system()
            if system == "Windows":
                icon_path = assets_dir / "icon.ico"
            elif system == "Darwin":
                icon_path = assets_dir / "icon.icns"
            else:  # Linux
                icon_path = assets_dir / "icon.png"

        # return str(exe_path), final_icon_path
        return str(exe_path), icon_path

    def _copy_icon_to_persistent_location(self, temp_icon_path):
        """Copy icon from temporary _MEIPASS to persistent location for Linux .desktop files"""
        try:
            import shutil

            # Get persistent directory
            if self.settings_manager and hasattr(self.settings_manager, "get"):
                persistent_dir = Path(
                    self.settings_manager.get("base_dir", Path.home() / ".mediatools")
                )
            else:
                persistent_dir = Path.home() / ".mediatools"

            persistent_dir.mkdir(parents=True, exist_ok=True)
            persistent_icon = persistent_dir / temp_icon_path.name

            # Copy if not already exists or if source is newer
            if (
                not persistent_icon.exists()
                or temp_icon_path.stat().st_mtime > persistent_icon.stat().st_mtime
            ):
                shutil.copy2(temp_icon_path, persistent_icon)
                self.logger.info(
                    f"Copied icon to persistent location: {persistent_icon}"
                )

            return str(persistent_icon)
        except Exception as e:
            self.logger.warning(f"Could not copy icon to persistent location: {e}")
            return str(temp_icon_path)

    def _create_windows_shortcut(self):
        """Windows shortcut creation with proper dependency handling"""
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

            print(
                f"Creating Windows shortcut at {shortcut_path} pointing to {exe_path} with icon {icon_path}"
            )

            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))  # Convert to string

            # Convert ALL paths to strings
            shortcut.Targetpath = str(exe_path)
            shortcut.WorkingDirectory = str(Path(exe_path).parent)
            shortcut.Description = (
                f"{self.app_name} - Download videos from various platforms"
            )

            # IconLocation needs string and optionally index
            if icon_path:
                shortcut.IconLocation = (
                    f"{str(icon_path)},0"  # Convert to string and add index
                )
            else:
                shortcut.IconLocation = (
                    f"{str(exe_path)},0"  # Use executable as icon source
                )

            shortcut.save()

            self.logger.info(f"Windows shortcut created: {shortcut_path}")
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

            self.logger.info(f"Windows batch shortcut created: {bat_path}")
            messagebox.showinfo(
                "Success",
                "Desktop shortcut created as batch file!\n"
                "(Install pywin32 for proper .lnk shortcut)",
            )
            return True
        except PermissionError:
            self.logger.error("Permission denied creating Windows shortcut")
            messagebox.showerror(
                "Permission Error",
                "Cannot write to Desktop. Please run as administrator or create shortcut manually.",
            )
            return False
        except Exception as e:
            self.logger.error(f"Manual Windows shortcut failed: {e}")
            messagebox.showerror("Error", f"Manual shortcut creation failed: {e}")
            return False

    def _create_linux_shortcut(self):
        """Linux .desktop file creation"""
        try:
            desktop = Path.home() / "Desktop"
            desktop_file = (
                desktop / f"{self.app_name.replace(' ', '-').lower()}.desktop"
            )

            exe_path, icon_path = self._get_executable_and_icon_paths()

            # Create desktop file content with proper quoting
            desktop_content = f"""[Desktop Entry]
    Version=1.0
    Type=Application
    Name={self.app_name}
    Comment=Download videos from various platforms
    Exec="{exe_path}"
    Path={Path(exe_path).parent}
    Icon={icon_path}
    Terminal=false
    StartupNotify=true
    Categories=AudioVideo;Video;Network;
    MimeType=text/uri-list;
    Keywords=video;download;youtube;yt-dlp;media;
    """

            with open(desktop_file, "w", encoding="utf-8") as f:
                f.write(desktop_content)

            # Make executable
            os.chmod(desktop_file, 0o755)

            # Mark as trusted (Ubuntu 22.04+)
            try:
                import subprocess

                # Try gio first (most common on Ubuntu)
                subprocess.run(
                    ["gio", "set", str(desktop_file), "metadata::trusted", "true"],
                    check=False,
                    capture_output=True,
                )

                # Try xattr but don't crash if it fails
                try:
                    subprocess.run(
                        ["xattr", "-w", "user.pika-trust", "yes", str(desktop_file)],
                        check=False,
                        capture_output=True,
                    )
                except FileNotFoundError:
                    # xattr not installed - that's fine
                    pass
                except Exception as e:
                    self.logger.debug(f"xattr failed (normal if not installed): {e}")

            except Exception as e:
                self.logger.warning(f"Could not mark desktop file as trusted: {e}")

            # Also install to applications menu
            apps_installed = False
            try:
                apps_dir = Path.home() / ".local/share/applications"
                apps_dir.mkdir(parents=True, exist_ok=True)
                apps_file = (
                    apps_dir / f"{self.app_name.replace(' ', '-').lower()}.desktop"
                )

                with open(apps_file, "w", encoding="utf-8") as f:
                    f.write(desktop_content)
                os.chmod(apps_file, 0o755)
                apps_installed = True
                self.logger.info(f"Linux app menu entry created: {apps_file}")
            except Exception as e:
                self.logger.warning(f"Could not create app menu entry: {e}")

            self.logger.info(f"Linux desktop shortcut created: {desktop_file}")

            # Inform user they may need to right-click and "Allow Launching"
            if apps_installed:
                messagebox.showinfo(
                    "Success",
                    "Desktop shortcut created!\n\n"
                    "Note: If you see a security warning, right-click the icon\n"
                    "and select 'Allow Launching' or 'Trust this application'.",
                )
            else:
                messagebox.showinfo(
                    "Success",
                    "Desktop shortcut created!\n\n"
                    "Note: If you see a security warning, right-click the icon\n"
                    "and select 'Allow Launching' or 'Trust this application'.",
                )

            return True

        except Exception as e:
            self.logger.error(f"Linux shortcut creation failed: {e}")
            messagebox.showerror("Error", f"Linux shortcut creation failed: {e}")
            return False

    def _create_mac_shortcut(self):
        try:
            desktop = Path.home() / "Desktop"
            exe_path, icon_path = self._get_executable_and_icon_paths()

            # Create .command file
            script_content = f"""#!/bin/bash
    cd "{Path(exe_path).parent}"
    ./"{Path(exe_path).name}"
    """
            script_path = desktop / f"{self.app_name}.command"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)

            # ✅ SET CUSTOM ICON using AppleScript
            if icon_path.exists():
                applescript = f"""
                tell application "Finder"
                    set theFile to POSIX file "{script_path}" as alias
                    set theIcon to POSIX file "{icon_path}" as alias
                    set icon of theFile to theIcon
                end tell
                """
                subprocess.run(["osascript", "-e", applescript], check=False)

            self.logger.info(f"macOS shortcut created: {script_path}")
            messagebox.showinfo("Success", "Desktop shortcut created!")
            return True
        except Exception as e:
            self.logger.error(f"macOS shortcut creation failed: {e}")
            return False

    def shortcut_exists(self):
        """Check if shortcut already exists on desktop"""
        desktop = Path.home() / "Desktop"
        system = platform.system()

        if system == "Windows":
            exists = (desktop / f"{self.app_name}.lnk").exists() or (
                desktop / f"{self.app_name}.bat"
            ).exists()
        elif system == "Darwin":
            exists = (desktop / f"{self.app_name}.command").exists()
        elif system == "Linux":
            exists = (
                desktop / f"{self.app_name.replace(' ', '-').lower()}.desktop"
            ).exists()
        else:
            exists = False

        self.logger.info(f"Shortcut exists check: {exists}")
        return exists

    def remove_desktop_shortcut(self):
        """Remove existing desktop shortcut"""
        system = platform.system()
        desktop = Path.home() / "Desktop"
        removed = False

        try:
            if system == "Windows":
                shortcut_path = desktop / f"{self.app_name}.lnk"
                bat_path = desktop / f"{self.app_name}.bat"
                if shortcut_path.exists():
                    shortcut_path.unlink()
                    removed = True
                if bat_path.exists():
                    bat_path.unlink()
                    removed = True

            elif system == "Darwin":
                shortcut_path = desktop / f"{self.app_name}.command"
                if shortcut_path.exists():
                    shortcut_path.unlink()
                    removed = True

            elif system == "Linux":
                shortcut_path = (
                    desktop / f"{self.app_name.replace(' ', '-').lower()}.desktop"
                )
                apps_path = (
                    Path.home()
                    / ".local/share/applications"
                    / f"{self.app_name.replace(' ', '-').lower()}.desktop"
                )
                if shortcut_path.exists():
                    shortcut_path.unlink()
                    removed = True
                if apps_path.exists():
                    apps_path.unlink()
                    removed = True

            if removed:
                self.logger.info("Desktop shortcut removed")
                messagebox.showinfo("Success", "Desktop shortcut removed!")
            else:
                messagebox.showinfo("Info", "No desktop shortcut found to remove")

            return removed

        except Exception as e:
            self.logger.error(f"Failed to remove shortcut: {e}")
            messagebox.showerror("Error", f"Could not remove shortcut: {e}")
            return False

    def ask_create_shortcut(self):
        """Ask user if they want to create a desktop shortcut"""
        # Don't ask if shortcut already exists
        if self.shortcut_exists():
            response = messagebox.askyesno(
                "Shortcut Exists",
                f"A desktop shortcut for {self.app_name} already exists.\n\n"
                "Would you like to create a new one? (This will replace the existing shortcut)",
            )
            if response:
                # Remove existing shortcut first
                self.remove_desktop_shortcut()
            else:
                return False

        root = tk.Tk()
        root.withdraw()  # Hide the main window

        response = messagebox.askyesno(
            "Create Desktop Shortcut",
            f"Would you like to create a desktop shortcut for {self.app_name}?",
        )

        if response:
            success = self.create_desktop_shortcut_cross_platform()
            if not success:
                self._show_manual_instructions()

        root.destroy()
        return response

    def _show_manual_instructions(self):
        """Show manual shortcut creation instructions"""
        system = platform.system()
        exe_path, _ = self._get_executable_and_icon_paths()

        if system == "Windows":
            instructions = f"""Manual shortcut creation:

1. Right-click on Desktop
2. Choose 'New' → 'Shortcut'  
3. Browse to: {exe_path}
4. Name it: {self.app_name}

Or right-click the executable and select 'Create shortcut'"""
        elif system == "Linux":
            instructions = f"""Manual shortcut creation:

1. Right-click on Desktop
2. Create new file: {self.app_name.replace(' ', '-')}.desktop
3. Copy the content below into the file:
   
[Desktop Entry]
Version=1.0
Type=Application
Name={self.app_name}
Exec={exe_path}
Path={Path(exe_path).parent}
Terminal=false

4. Make it executable: chmod +x filename.desktop"""
        else:  # macOS
            instructions = f"""Manual shortcut creation:

1. Open Finder and navigate to: {Path(exe_path).parent}
2. Drag '{Path(exe_path).name}' to the Desktop while holding Option (⌥)
3. This will create an alias (shortcut)

Or drag to Applications folder for easier access"""

        messagebox.showinfo("Manual Setup", instructions)

    def first_run_setup(self):
        """Check if first run and offer shortcut creation (only if no shortcut exists)"""
        # Don't offer if shortcut already exists
        if self.shortcut_exists():
            self.logger.info("Shortcut exists, skipping first-run setup")
            return

        # Use settings manager's data directory if available
        if self.settings_manager and hasattr(self.settings_manager, "get"):
            data_dir = Path(
                self.settings_manager.get("data_dir", Path.home() / ".mediatools")
            )
        else:
            data_dir = Path.home() / ".mediatools"

        first_run_file = data_dir / "first_run.flag"

        if not first_run_file.exists():
            # Create data directory
            data_dir.mkdir(parents=True, exist_ok=True)

            # Ask about shortcut
            self.ask_create_shortcut()

            # Mark as not first run
            try:
                first_run_file.touch()
                self.logger.info("First run setup completed")
            except Exception as e:
                self.logger.warning(f"Could not create first run flag: {e}")


# Standalone functions for backward compatibility
def create_desktop_shortcut_cross_platform():
    """Standalone function - creates shortcut creator and runs it"""
    creator = ShortcutCreator()
    return creator.create_desktop_shortcut_cross_platform()


def ask_create_shortcut():
    """Standalone function"""
    creator = ShortcutCreator()
    return creator.ask_create_shortcut()


def first_run_setup(settings_manager=None):
    """Standalone function with optional settings manager"""
    creator = ShortcutCreator(settings_manager)
    return creator.first_run_setup()


def shortcut_exists():
    """Standalone function to check if shortcut exists"""
    creator = ShortcutCreator()
    return creator.shortcut_exists()


def remove_desktop_shortcut():
    """Standalone function to remove shortcut"""
    creator = ShortcutCreator()
    return creator.remove_desktop_shortcut()



