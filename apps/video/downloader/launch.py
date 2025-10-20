# launch.py
import sys
from pathlib import Path

# Get paths
launch_file = Path(__file__).resolve()
app_dir = launch_file.parent                    # apps/video/downloader/
repo_root = app_dir.parent.parent.parent        # mediatools/
src_dir = repo_root / 'src'                     # mediatools/src/

# Add to Python path
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(app_dir))

# Import and run
from video_downloader import main

if __name__ == "__main__":
    main()