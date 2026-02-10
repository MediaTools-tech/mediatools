from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Video Transcoder"
    DEBUG: bool = True
    
    # Storage
    UPLOAD_DIR: str = "./storage/uploads"
    TEMP_DIR: str = "./storage/temp"
    OUTPUT_DIR: str = "./storage/outputs"
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB
    
    # FFmpeg
    FFMPEG_PATH: str = "ffmpeg"
    VIDEO_CODEC: str = "libaom-av1"
    
    # Redis (Phase 2)
    REDIS_URL: str = "redis://localhost:6379"
    
    # Database (Phase 2)
    DATABASE_URL: str = "postgresql://user:pass@localhost/transcoder"
    
    class Config:
        env_file = ".env"

settings = Settings()