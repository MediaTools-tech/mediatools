import requests
from pathlib import Path
import json
import sys
import os

class AppUpdateChecker:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.local_version_file = self.settings._get_bundle_resource(
            Path("mediatools") / "video" / "transcoder" / "data" / "version.txt"
        )
        self.github_repo_url = "https://raw.githubusercontent.com/MediaTools-tech/mediatools/main"

    def get_local_app_version(self) -> str:
        """Reads the local application version from version.txt."""
        try:
            if self.local_version_file.exists():
                return self.local_version_file.read_text().strip()
        except Exception as e:
            print(f"Error reading local app version: {e}")
        return "0.0.0" # Default or error version

    def get_remote_app_version(self) -> str:
        """Fetches the latest application version from GitHub."""
        try:
            # Construct the URL for the remote version.txt
            remote_version_url = f"{self.github_repo_url}/src/mediatools/video/transcoder/data/version.txt"
            
            response = requests.get(remote_version_url, timeout=5)
            response.raise_for_status() # Raise an exception for HTTP errors
            return response.text.strip()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching remote app version: {e}")
        return "0.0.0" # Default or error version if unable to fetch

    def is_app_up_to_date(self) -> bool:
        """Compares local and remote application versions."""
        local_version_str = self.get_local_app_version()
        remote_version_str = self.get_remote_app_version()

        if local_version_str == "0.0.0" or remote_version_str == "0.0.0":
            # If unable to get versions, assume up-to-date or handle as an error case
            return True

        # Simple string comparison works for semantic versioning like X.Y.Z
        # For more robust comparison, one might parse versions (e.g., using packaging.version.parse)
        # but for now, string comparison is sufficient given the expected format.
        return local_version_str >= remote_version_str
