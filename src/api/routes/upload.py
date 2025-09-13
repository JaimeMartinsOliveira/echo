from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import os
from datetime import datetime
import logging
from ...services.file_handler import FileHandler
from ...services.trigger_client import TriggerClient
from ...models.transcription import TranscriptionRequest, TranscriptionResponse, TranscriptionStatus
from ...utils.validators import validate_file, validate_url
from ...utils.helpers import estimate_transcription_time
from ...database.connection import get_db
from ...database.models import Job

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload/file", response_model=TranscriptionResponse)
async def upload_file(
        request: Request,
        db: Session = Depends(get_db),
        file: UploadFile = File(...),
        language: str = Form(default="auto"),
        webhook_url: Optional[str] = Form(default=None)
):
    """Upload de arquivo de áudio/vídeo para transcrição"""

    logger.info(f"Recebido upload: {file.filename}, tamanho: {file.size}")

    # Validar arquivo
    validation_result = await validate_file(file)
    if not validation_result["valid"]:
        logger.error(f"Arquivo inválido: {validation_result['message']}")
        raise HTTPException(status_code=400, detail=validation_result["message"])

    job_id = str(uuid.uuid4())
    file_path = None

    try:
        logger.info(f"[{job_id}] Processando upload do arquivo: {file.filename}")

        # Salvar arquivo PRIMEIRO
        file_handler = FileHandler()
        file_path = await file_handler.save_upload(file, job_id)
        logger.info(f"[{job_id}] Arquivo salvo em: {file_path}")

        # Verificar se arquivo foi realmente salvo
        if not os.path.exists(file_path):
            raise Exception(f"Falha ao salvar arquivo em: {file_path}")

        # Criar registro no banco de dados
        db_job = Job(
            id=job_id,
            status=TranscriptionStatus.PENDING,
            file_path=file_path,  # Arquivo local
            language=language,
            webhook_url=webhook_url,
            job_data={
                "original_filename": file.filename,
                "file_size": validation_result.get("size", 0),
                "mime_type": validation_result.get("mime_type", "unknown")
            }
        )

        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        logger.info(f"[{job_id}] Job criado no banco de dados")

        # Criar job no Trigger - PASSAR O CAMINHO DO ARQUIVO
        trigger_client = request.app.state.trigger_client
        trigger_job_id = await trigger_client.create_transcription_job(
            job_id=job_id,
            file_path=file_path,  # Passar caminho do arquivo local
            language=language,
            webhook_url=webhook_url or f"{os.getenv('APP_URL', 'http://localhost:8000')}/webhooks/transcription"
        )

        logger.info(f"[{job_id}] Job criado no Trigger com ID: {trigger_job_id}")

        # Atualizar registro com trigger_job_id
        db_job.trigger_job_id = trigger_job_id
        db.commit()

        return TranscriptionResponse(
            job_id=job_id,
            status=TranscriptionStatus.PENDING,
            message="Arquivo recebido e job de transcrição criado",
            estimated_time=estimate_transcription_time(validation_result.get("size", 0))
        )

    except Exception as e:
        logger.error(f"[{job_id}] Erro no upload: {str(e)}")

        # Rollback em caso de erro
        db.rollback()

        # Limpar arquivo se foi salvo
        if file_path and os.path.exists(file_path):
            try:
                file_handler = FileHandler()
                await file_handler.delete_file(file_path)
                logger.info(f"[{job_id}] Arquivo removido após erro: {file_path}")
            except Exception as cleanup_error:
                logger.warning(f"[{job_id}] Erro ao limpar arquivo: {cleanup_error}")

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

    url_str = str(transcription_request.url)
    logger.info(f"Recebida URL para transcrição: {url_str}")

    # Validar URL
    if not await validate_url(url_str):
        logger.error(f"URL inválida ou inacessível: {url_str}")
        raise HTTPException(status_code=400, detail="URL inválida ou inacessível")

    job_id = str(uuid.uuid4())

    try:
        logger.info(f"[{job_id}] Criando job para URL: {url_str}")

        # Criar registro no banco de dados
        db_job = Job(
            id=job_id,
            status=TranscriptionStatus.PENDING,
            file_url=url_str,  # URL externa
            language=transcription_request.language,
            webhook_url=str(transcription_request.webhook_url) if transcription_request.webhook_url else None,
            job_data=transcription_request.metadata or {}
        )

        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        logger.info(f"[{job_id}] Job criado no banco de dados para URL")

        # Criar job no Trigger - PASSAR A URL
        trigger_client = request.app.state.trigger_client
        trigger_job_id = await trigger_client.create_transcription_job(
            job_id=job_id,
            file_url=url_str,  # Passar URL
            language=transcription_request.language,
            webhook_url=str(
                transcription_request.webhook_url) if transcription_request.webhook_url else f"{os.getenv('APP_URL', 'http://localhost:8000')}/webhooks/transcription"
        )

        logger.info(f"[{job_id}] Job criado no Trigger com ID: {trigger_job_id}")

        # Atualizar registro com trigger_job_id
        db_job.trigger_job_id = trigger_job_id
        db.commit()

        return TranscriptionResponse(
            job_id=job_id,
            status=TranscriptionStatus.PENDING,
            message="Job de transcrição criado a partir da URL",
            estimated_time=None  # Não podemos estimar sem o arquivo local
        )

    except Exception as e:
        logger.error(f"[{job_id}] Erro ao processar URL: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


def estimate_transcription_time(file_size_bytes: int) -> int:
    """Estima tempo de transcrição baseado no tamanho do arquivo"""
    # Estimativa: ~1 minuto de processamento para cada 10MB
    estimated_minutes = max(1, file_size_bytes // (10 * 1024 * 1024))
    return estimated_minutes * 60  # retorna em segundos