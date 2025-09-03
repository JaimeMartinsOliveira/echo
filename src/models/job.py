from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from .transcription import TranscriptionStatus

class Job(BaseModel):
    id: str
    status: TranscriptionStatus
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    language: str = "auto"
    webhook_url: Optional[str] = None
    trigger_job_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = {}