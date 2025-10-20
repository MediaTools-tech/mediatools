#!/bin/bash

echo "Waiting for app to fully exit..."
sleep 3

echo "Starting cleanup of $# patterns..."

total_deleted=0

for base_path in "$@"; do
    # Extract folder and base name
    folder_path=$(dirname "$base_path")
    base_name=$(basename "$base_path")
    
    echo ""
    echo "Cleaning up: $base_name in $folder_path"
    
    # Check if folder exists
    if [ ! -d "$folder_path" ]; then
        echo "✗ Folder not found: $folder_path"
        continue
    fi
    
    # Change to folder and delete files
    cd "$folder_path"
    base_deleted=0
    
    for file in "$base_name"*.*; do
        if [ -f "$file" ]; then
            echo "Deleting: $(basename "$file")"
            if rm -f "$file" 2>/dev/null; then
                echo "✓ Deleted: $(basename "$file")"
                base_deleted=$((base_deleted + 1))
                total_deleted=$((total_deleted + 1))
            else
                echo "✗ Failed: $(basename "$file")"
            fi
        fi
    done
    
    if [ $base_deleted -eq 0 ]; then
        echo "No files found for: $base_name"
    fi
done

echo ""
echo "Cleanup completed! Total files deleted: $total_deleted"
sleep 2
