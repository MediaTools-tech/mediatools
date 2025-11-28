"""MediaTools - Media Tools Library"""

__version__ = "0.1.0"
__author__ = "MediaTools Tech"
__description__ = "Media tools for video, audio, image, and speech"

# Import main modules
try:
    from . import video, audio, image, speech

    __all__ = ["video", "audio", "image", "speech"]
except ImportError:
    # During setup, imports might fail
    __all__ = []
