from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TranscriptionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TranscriptionRequest(BaseModel):
    url: Optional[HttpUrl] = None
    language: Optional[str] = Field(default="auto", description="Código do idioma ou 'auto' para detecção automática")
    webhook_url: Optional[HttpUrl] = None
    metadata: Optional[Dict[str, Any]] = {}

class TranscriptionResponse(BaseModel):
    job_id: str
    status: TranscriptionStatus
    message: str
    estimated_time: Optional[int] = None

class TranscriptionResult(BaseModel):
    job_id: str
    status: TranscriptionStatus
    text: Optional[str] = None
    segments: Optional[List[Dict[str, Any]]] = None
    language: Optional[str] = None
    duration: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}