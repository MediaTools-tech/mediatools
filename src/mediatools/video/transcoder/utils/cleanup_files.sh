#!/usr/bin/env bash
# cleanup_files.sh - Unix-like cleanup utility

echo "Waiting for app to fully exit..."
sleep 5

echo "Starting cleanup of $@ patterns..."

TOTAL_DELETED=0

for PATTERN in "$@"; do
    FOLDER_PATH=$(dirname "$PATTERN")
    BASE_NAME=$(basename "$PATTERN")
    
    echo ""
    echo "Cleaning up: $BASE_NAME in $FOLDER_PATH"
    
    if [ ! -d "$FOLDER_PATH" ]; then
        echo "✗ Folder not found: $FOLDER_PATH"
        continue
    fi
    
    BASE_DELETED=0
    # Use find to locate files starting with BASE_NAME in FOLDER_PATH
    # and delete them
    while IFS= read -r FILE; do
        if [ -f "$FILE" ]; then
            echo "Deleting: $(basename "$FILE")"
            rm -f "$FILE"
            if [ $? -eq 0 ]; then
                echo "✓ Deleted: $(basename "$FILE")"
                ((BASE_DELETED++))
                ((TOTAL_DELETED++))
            else
                echo "✗ Failed: $(basename "$FILE")"
            fi
        fi
    done < <(find "$FOLDER_PATH" -maxdepth 1 -name "${BASE_NAME}*")
    
    if [ $BASE_DELETED -eq 0 ]; then
        echo "No files found for: $BASE_NAME"
    fi
done

echo ""
echo "Cleanup completed! Total files deleted: $TOTAL_DELETED"
sleep 2
