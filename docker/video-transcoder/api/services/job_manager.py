from datetime import datetime
from typing import Dict, List, Optional
from api.services.storage import delete_job_files

class JobManager:
    """
    In-memory job manager for Phase 1.
    Will be replaced with Redis/PostgreSQL in Phase 2.
    """
    
    def __init__(self):
        self.jobs: Dict[str, dict] = {}
    
    def create_job(self, job_id: str, filename: str, input_path: str, options: dict) -> dict:
        """Create a new transcoding job"""
        job = {
            "job_id": job_id,
            "filename": filename,
            "status": "queued",
            "progress": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None,
            "error_message": None,
            "input_path": input_path,
            "output_path": None,
            "file_size_mb": None,
            "options": options
        }
        self.jobs[job_id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    def update_job(self, job_id: str, **kwargs) -> bool:
        """Update job fields"""
        if job_id not in self.jobs:
            return False
        
        self.jobs[job_id].update(kwargs)
        self.jobs[job_id]["updated_at"] = datetime.utcnow()
        return True
    
    def complete_job(self, job_id: str, output_path: str, file_size_mb: float) -> bool:
        """Mark job as completed"""
        if job_id not in self.jobs:
            return False
        
        self.jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "output_path": output_path,
            "file_size_mb": file_size_mb,
            "completed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        return True
    
    def fail_job(self, job_id: str, error_message: str) -> bool:
        """Mark job as failed"""
        if job_id not in self.jobs:
            return False
        
        self.jobs[job_id].update({
            "status": "failed",
            "error_message": error_message,
            "updated_at": datetime.utcnow()
        })
        return True
    
    def list_jobs(self, status: str = None, limit: int = 50) -> List[dict]:
        """List jobs, optionally filtered by status"""
        jobs = list(self.jobs.values())
        
        # Filter by status if provided
        if status:
            jobs = [job for job in jobs if job["status"] == status]
        
        # Sort by created_at descending (newest first)
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        
        return jobs[:limit]
    
    def delete_job(self, job_id: str) -> bool:
        """Delete job and its files"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        # Delete associated files
        delete_job_files(job["input_path"], job.get("output_path"))
        
        # Remove from memory
        del self.jobs[job_id]
        return True
    
    def get_stats(self) -> dict:
        """Get job statistics"""
        total = len(self.jobs)
        completed = sum(1 for job in self.jobs.values() if job["status"] == "completed")
        failed = sum(1 for job in self.jobs.values() if job["status"] == "failed")
        processing = sum(1 for job in self.jobs.values() if job["status"] == "processing")
        queued = sum(1 for job in self.jobs.values() if job["status"] == "queued")
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "processing": processing,
            "queued": queued
        }

# Global singleton instance
job_manager = JobManager()