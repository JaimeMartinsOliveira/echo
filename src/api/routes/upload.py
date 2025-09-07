from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import os
from datetime import datetime
from ...services.file_handler import FileHandler
from ...services.trigger_client import TriggerClient
from ...models.transcription import TranscriptionRequest, TranscriptionResponse, TranscriptionStatus
from ...utils.validators import validate_file, validate_url
from ...utils.helpers import estimate_transcription_time
from ...database.connection import get_db
from ...database.models import Job

router = APIRouter()


@router.post("/upload/file", response_model=TranscriptionResponse)
async def upload_file(
        request: Request,
        db: Session = Depends(get_db),
        file: UploadFile = File(...),
        language: str = Form(default="auto"),
        webhook_url: Optional[str] = Form(default=None)
):
    """Upload de arquivo de áudio/vídeo para transcrição"""

    # Validar arquivo
    validation_result = await validate_file(file)
    if not validation_result["valid"]:
        raise HTTPException(status_code=400, detail=validation_result["message"])

    try:
        # Gerar ID único para o job
        job_id = str(uuid.uuid4())

        # Salvar arquivo
        file_handler = FileHandler()
        file_path = await file_handler.save_upload(file, job_id)

        # CRÍTICO: Criar registro no banco de dados PRIMEIRO
        db_job = Job(
            id=job_id,
            status=TranscriptionStatus.PENDING,
            file_path=file_path,
            language=language,
            webhook_url=webhook_url,
            metadata={
                "original_filename": file.filename,
                "file_size": validation_result.get("size", 0),
                "mime_type": validation_result.get("mime_type", "unknown")
            }
        )

        db.add(db_job)
        db.commit()
        db.refresh(db_job)

        # Criar job no Trigger
        trigger_client = request.app.state.trigger_client
        trigger_job_id = await trigger_client.create_transcription_job(
            job_id=job_id,
            file_path=file_path,
            language=language,
            webhook_url=webhook_url
        )

        # CRÍTICO: Atualizar registro com trigger_job_id
        db_job.trigger_job_id = trigger_job_id
        db.commit()

        return TranscriptionResponse(
            job_id=job_id,
            status=TranscriptionStatus.PENDING,
            message="Arquivo recebido e job de transcrição criado",
            estimated_time=estimate_transcription_time(validation_result.get("size", 0))
        )

    except Exception as e:
        # Rollback em caso de erro
        db.rollback()
        # Limpar arquivo se foi salvo
        if 'file_path' in locals():
            file_handler.delete_file(file_path)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.post("/upload/url", response_model=TranscriptionResponse)
async def upload_from_url(
        request: Request,
        transcription_request: TranscriptionRequest,
        db: Session = Depends(get_db)
):
    """Transcrição a partir de URL de áudio/vídeo"""

    if not transcription_request.url:
        raise HTTPException(status_code=400, detail="URL é obrigatória")

    # Validar URL
    if not await validate_url(str(transcription_request.url)):
        raise HTTPException(status_code=400, detail="URL inválida ou inacessível")

    try:
        # Gerar ID único para o job
        job_id = str(uuid.uuid4())

        # CRÍTICO: Criar registro no banco de dados PRIMEIRO
        db_job = Job(
            id=job_id,
            status=TranscriptionStatus.PENDING,
            file_url=str(transcription_request.url),
            language=transcription_request.language,
            webhook_url=str(transcription_request.webhook_url) if transcription_request.webhook_url else None,
            metadata=transcription_request.metadata or {}
        )

        db.add(db_job)
        db.commit()
        db.refresh(db_job)

        # Criar job no Trigger
        trigger_client = request.app.state.trigger_client
        trigger_job_id = await trigger_client.create_transcription_job(
            job_id=job_id,
            file_url=str(transcription_request.url),
            language=transcription_request.language,
            webhook_url=str(transcription_request.webhook_url) if transcription_request.webhook_url else None
        )

        # CRÍTICO: Atualizar registro com trigger_job_id
        db_job.trigger_job_id = trigger_job_id
        db.commit()

        return TranscriptionResponse(
            job_id=job_id,
            status=TranscriptionStatus.PENDING,
            message="Job de transcrição criado a partir da URL",
            estimated_time=None  # Não podemos estimar sem o arquivo local
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


def estimate_transcription_time(file_size_bytes: int) -> int:
    """Estima tempo de transcrição baseado no tamanho do arquivo"""
    # Estimativa: ~1 minuto de processamento para cada 10MB
    estimated_minutes = max(1, file_size_bytes // (10 * 1024 * 1024))
    return estimated_minutes * 60  # retorna em segundos