from setuptools import setup, find_packages

setup(
    name="mediatools-video-downloader",
    version="2.1.0",
    description="A cross-platform video and audio downloader application for downloading media from various platforms.",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    keywords=["video downloader", "audio downloader", "youtube downloader", "yt-dlp", "gui", "mediatools"],
    python_requires=">=3.7",
)
