import os
import shutil
from pathlib import Path
from fastapi import UploadFile
from api.config import settings

async def save_upload_file(upload_file: UploadFile, job_id: str) -> str:
    """
    Save uploaded file to storage directory.
    
    Args:
        upload_file: FastAPI UploadFile object
        job_id: Unique job identifier
    
    Returns:
        Path to saved file
    """
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Generate file path with job_id prefix
    file_extension = Path(upload_file.filename).suffix
    file_path = os.path.join(settings.UPLOAD_DIR, f"{job_id}{file_extension}")
    
    # Save file in chunks (memory efficient for large files)
    with open(file_path, "wb") as buffer:
        chunk_size = 1024 * 1024  # 1MB chunks
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            buffer.write(chunk)
    
    return file_path

def get_output_path(job_id: str) -> Path:

    """Generate output file path for transcoded video"""

    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    return Path(settings.OUTPUT_DIR) / job_id



def delete_job_files(input_path: str, output_path: str = None):

    """Delete input and output files for a job"""

    try:

        if input_path and os.path.exists(input_path):

            os.remove(input_path)

        if output_path and os.path.exists(output_path):

            os.remove(output_path)

    except Exception as e:

        print(f"Error deleting files: {e}")

def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes"""
    if not os.path.exists(file_path):
        return 0.0
    size_bytes = os.path.getsize(file_path)
    return round(size_bytes / (1024 * 1024), 2)