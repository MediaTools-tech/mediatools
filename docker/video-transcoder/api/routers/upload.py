from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from api.services.storage import save_upload_file
from api.services.job_manager import job_manager
from api.services.transcoder import transcode_video
from api.models import JobResponse, TranscodingOptions
import uuid
import json

router = APIRouter()

@router.post("/upload", response_model=JobResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: str = Form(...)
):
    """
    Upload a video file for transcoding.

    - Accepts video files (mp4, avi, mov, mkv)
    - Returns job_id for tracking
    - Transcoding happens in background
    """

    # Validate file type
    allowed_types = ["video/mp4", "video/x-msvideo", "video/quicktime", "video/x-matroska", "video/webm"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Parse options
    try:
        options_data = json.loads(options)
        transcoding_options = TranscodingOptions(**options_data)
    except (json.JSONDecodeError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid options format: {e}")

    # Generate job ID
    job_id = str(uuid.uuid4())

    try:
        # Save uploaded file
        input_path = await save_upload_file(file, job_id)

        # Create job
        job = job_manager.create_job(
            job_id=job_id,
            filename=file.filename,
            input_path=input_path,
            options=transcoding_options.dict()
        )

        # Start transcoding in background
        background_tasks.add_task(
            transcode_video,
            job_id=job_id,
            input_path=input_path,
            options=transcoding_options
        )

        return JobResponse(**job)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")