import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "ffmpeg_available" in data

def test_readiness_check():
    """Test readiness check endpoint"""
    response = client.get("/api/readiness")
    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert "checks" in data

def test_list_jobs_empty():
    """Test listing jobs when none exist"""
    response = client.get("/api/jobs/")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert "total" in data
    assert isinstance(data["jobs"], list)

def test_get_nonexistent_job():
    """Test getting a job that doesn't exist"""
    response = client.get("/api/jobs/nonexistent-id")
    assert response.status_code == 404

def test_upload_invalid_file_type():
    """Test uploading invalid file type"""
    files = {"file": ("test.txt", b"not a video", "text/plain")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]

# Add more tests for actual video upload, status checking, etc.
# These would require test video files and more complex setup

def test_cancel_nonexistent_job():
    """Test cancelling a job that doesn't exist"""
    response = client.post("/api/jobs/nonexistent-id/cancel")
    assert response.status_code == 400
    assert "Could not cancel job" in response.json()["detail"]