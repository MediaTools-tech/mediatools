from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from api.services.job_manager import job_manager
from api.models import JobResponse, JobListResponse
from typing import List
import os

router = APIRouter()

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get status of a specific job"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**job)

@router.get("/", response_model=JobListResponse)
async def list_jobs(status: str = None, limit: int = 50):
    """
    List all jobs, optionally filtered by status.
    
    - status: queued, processing, completed, failed (optional)
    - limit: maximum number of jobs to return (default: 50)
    """
    jobs = job_manager.list_jobs(status=status, limit=limit)
    return JobListResponse(jobs=[JobResponse(**job) for job in jobs])

@router.get("/{job_id}/download")
async def download_transcoded_video(job_id: str):
    """Download the transcoded video file"""
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job['status']}"
        )

    output_path = job.get("output_path")
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Output file not found")

    # Determine download filename: original filename base + transcoded extension
    original_filename_base = os.path.splitext(job["filename"])[0]
    transcoded_extension = os.path.splitext(os.path.basename(output_path))[1]
    download_filename = original_filename_base + transcoded_extension

    media_types = {
        "mp4": "video/mp4",
        "mkv": "video/x-matroska",
        "avi": "video/x-msvideo",
        "webm": "video/webm",
        "mov": "video/quicktime"
    }
    media_type = media_types.get(transcoded_extension.lstrip("."), "application/octet-stream")

    return FileResponse(
        path=output_path,
        media_type=media_type,
        filename=download_filename
    )

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running transcoding job"""
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not cancel job. Job not found or not processing.")
    return {"message": "Job cancellation initiated", "job_id": job_id}

@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its associated files"""
    success = job_manager.delete_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": "Job deleted successfully", "job_id": job_id}