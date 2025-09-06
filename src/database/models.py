from sqlalchemy import Column, String, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from .connection import Base
from ..models.transcription import TranscriptionStatus
import uuid

class Job(Base):
    __tablename__ = "jobs"

    # Chaves primárias e identificadores
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trigger_job_id = Column(String, nullable=True, index=True)

    # Status e timestamps
    status = Column(SQLEnum(TranscriptionStatus), nullable=False, default=TranscriptionStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Configuração do job
    file_path = Column(String, nullable=True)
    file_url = Column(String, nullable=True)
    language = Column(String, default="auto", nullable=False)
    webhook_url = Column(String, nullable=True)

    # Resultados da transcrição
    result_text = Column(Text, nullable=True)
    result_segments = Column(JSON, nullable=True)
    result_language = Column(String, nullable=True)
    duration = Column(String, nullable=True)  # Armazenar como string para flexibilidade

    # Metadados e erros
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True, default=dict)

    def to_dict(self):
        """Converte o modelo SQLAlchemy para dicionário"""
        return {
            "id": self.id,
            "status": self.status,
            "trigger_job_id": self.trigger_job_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "file_path": self.file_path,
            "file_url": self.file_url,
            "language": self.language,
            "webhook_url": self.webhook_url,
            "result_text": self.result_text,
            "result_segments": self.result_segments,
            "result_language": self.result_language,
            "duration": self.duration,
            "error_message": self.error_message,
            "metadata": self.metadata or {}
        }