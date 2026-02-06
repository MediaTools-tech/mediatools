#!/usr/bin/env bash
# build_onedir.sh - Cross-platform build script (folder distribution)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SRC_DIR="$REPO_ROOT/src/mediatools/video/downloader"

# Platform detection
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
        echo "Platform: Windows (Git Bash)"
        REPO_ROOT=$(cygpath -m "$REPO_ROOT")
        SRC_DIR=$(cygpath -m "$SRC_DIR")
        APP_DIR=$(cygpath -m "$APP_DIR")
        PLATFORM_UTIL="cleanup_files.bat"
        PYTHON_CMD="python"
        SEP=";"  # Windows separator
        EXTRA_IMPORTS="--hidden-import=winshell --hidden-import=win32com --hidden-import=win32com.client"
        ;;
    Darwin*)
        echo "Platform: macOS"
        PLATFORM_UTIL="cleanup_files.sh"
        PYTHON_CMD="python3"
        SEP=":"  # Unix separator
        EXTRA_IMPORTS=""
        ;;
    Linux*)
        echo "Platform: Linux"
        PLATFORM_UTIL="cleanup_files.sh"
        PYTHON_CMD="python3"
        SEP=":"  # Unix separator
        EXTRA_IMPORTS=""
        ;;
    *)
        echo "Platform: Unknown"
        PLATFORM_UTIL="cleanup_files.sh"
        PYTHON_CMD="python"
        SEP=":"
        EXTRA_IMPORTS=""
        ;;
esac

echo "Repository root: $REPO_ROOT"
echo "Source directory: $SRC_DIR"
echo "Data separator: '$SEP'"
echo ""

# Check if bin folder exists (optional - contains ffmpeg binaries)
BIN_DATA=""
if [ -d "$SRC_DIR/bin" ]; then
    echo "Including bin folder (ffmpeg binaries found)"
    BIN_DATA="--add-data=$SRC_DIR/bin${SEP}bin"
else
    echo "Skipping bin folder (not found - will use system ffmpeg)"
fi

echo "Cleaning previous builds..."
rm -rf build/ dist/

echo "Building folder distribution..."
$PYTHON_CMD -m PyInstaller \
  --onedir \
  --windowed \
  --noupx \
  --name "mt-vdl" \
  --paths="$REPO_ROOT/src" \
  --icon="$SRC_DIR/assets/icon.ico" \
  --add-data="$SRC_DIR/data${SEP}data" \
  $BIN_DATA \
  --add-data="$SRC_DIR/utils/$PLATFORM_UTIL${SEP}utils" \
  --add-data="$SRC_DIR/assets${SEP}assets" \
  --add-data="$APP_DIR/docs/UserGuide.pdf${SEP}docs" \
  --add-data="$APP_DIR/README.md${SEP}docs" \
  --add-data="$REPO_ROOT/LICENSE${SEP}docs" \
  --hidden-import=mediatools \
  --hidden-import=mediatools.video.downloader \
  --hidden-import=mediatools.video.downloader.core \
  --hidden-import=mediatools.video.downloader.gui \
  --hidden-import=mediatools.video.downloader.utils \
  --hidden-import=mediatools.video.downloader.compat \
  $EXTRA_IMPORTS \
  --clean \
  "$APP_DIR/launch.py"

echo ""
echo "✓ Build complete!"
echo "Output: dist/mt-vdl/"

