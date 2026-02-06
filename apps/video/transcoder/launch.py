# launch.py
import os
import sys
from pathlib import Path
import tkinter as tk

# Get paths
launch_file = Path(__file__).resolve()
app_dir = launch_file.parent                    # apps/video/transcoder/
repo_root = app_dir.parent.parent.parent        # mediatools/
src_dir = repo_root / 'src'                     # mediatools/src/

# Add to Python path
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# Import and run
from video_transcoder import VideoTranscoderApp

def main():
    root = tk.Tk()
    app = VideoTranscoderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
