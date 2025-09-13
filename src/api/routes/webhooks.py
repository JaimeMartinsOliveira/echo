from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import json
import os
from ...database.connection import get_db
from ...database.models import Job
from ...models.transcription import TranscriptionStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/transcription")
async def transcription_webhook(
        request: Request,
        db: Session = Depends(get_db)
):
    """Recebe notificações de status dos jobs de transcrição"""

    try:
        payload = await request.json()
        job_id = payload.get("job_id")
        status = payload.get("status")

        logger.info(f"[{job_id}] Webhook recebido: {status}")
        logger.debug(f"[{job_id}] Payload completo: {payload}")

        if not job_id:
            raise HTTPException(status_code=400, detail="job_id é obrigatório")

        # Buscar job no banco de dados
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if not db_job:
            logger.error(f"[{job_id}] Job não encontrado no banco de dados")
            raise HTTPException(status_code=404, detail="Job não encontrado")

        # Processar baseado no status
        if status == "completed":
            await save_transcription_result(db, db_job, payload)
            logger.info(f"[{job_id}] Resultado salvo com sucesso")

        elif status == "failed":
            await save_transcription_error(db, db_job, payload)
            logger.error(f"[{job_id}] Falha registrada: {payload.get('error_message', 'Erro desconhecido')}")

        elif status == "processing":
            # Atualizar status para processing
            db_job.status = TranscriptionStatus.PROCESSING
            db_job.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"[{job_id}] Status atualizado para: processing")

        # Salvar no Redis se disponível
        if hasattr(request.app.state, 'redis_client') and request.app.state.redis_client:
            await save_to_redis_cache(request.app.state.redis_client, job_id, db_job.to_dict())

        return JSONResponse(
            status_code=200,
            content={"message": "Webhook processado com sucesso", "job_id": job_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno")


async def save_transcription_result(db: Session, job: Job, payload: dict):
    """Salva resultado da transcrição concluída"""
    try:
        logger.info(f"[{job.id}] Salvando resultado da transcrição")

        # Atualizar status e resultados
        job.status = TranscriptionStatus.COMPLETED
        job.result_text = payload.get("text")
        job.result_segments = payload.get("segments", [])
        job.result_language = payload.get("language")
        job.duration = str(payload.get("duration")) if payload.get("duration") else None
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()

        # Limpar mensagem de erro se existir
        job.error_message = None

        db.commit()
        logger.info(f"[{job.id}] Resultado salvo no banco de dados")

        # Limpar arquivo temporário APENAS se for upload local (não URL)
        if job.file_path and not job.file_url and os.path.exists(job.file_path):
            try:
                # Aguardar um pouco antes de limpar para garantir que o processamento terminou
                import asyncio
                await asyncio.sleep(2)

                os.remove(job.file_path)
                logger.info(f"[{job.id}] Arquivo local removido: {job.file_path}")
            except Exception as e:
                logger.warning(f"[{job.id}] Erro ao remover arquivo local: {e}")

    except Exception as e:
        db.rollback()
        logger.error(f"[{job.id}] Erro ao salvar resultado da transcrição: {e}")
        raise


async def save_transcription_error(db: Session, job: Job, payload: dict):
    """Salva erro da transcrição"""
    try:
        logger.info(f"[{job.id}] Salvando erro da transcrição")

        job.status = TranscriptionStatus.FAILED
        job.error_message = payload.get("error_message", "Erro desconhecido durante a transcrição")
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()

        db.commit()
        logger.info(f"[{job.id}] Erro salvo no banco de dados")

        # Limpar arquivo temporário em caso de erro também (apenas uploads locais)
        if job.file_path and not job.file_url and os.path.exists(job.file_path):
            try:
                os.remove(job.file_path)
                logger.info(f"[{job.id}] Arquivo local removido após erro: {job.file_path}")
            except Exception as e:
                logger.warning(f"[{job.id}] Erro ao remover arquivo local após falha: {e}")

    except Exception as e:
        db.rollback()
        logger.error(f"[{job.id}] Erro ao salvar erro da transcrição: {e}")
        raise


async def save_to_redis_cache(redis_client, job_id: str, job_data: dict):
    """Salva resultado no cache Redis"""
    try:
        # Salvar por 24 horas (86400 segundos)
        await redis_client.setex(
            f"job:{job_id}",
            86400,
            json.dumps(job_data, default=str, ensure_ascii=False)
        )
        logger.debug(f"[{job_id}] Job salvo no cache Redis")
    except Exception as e:
        logger.warning(f"[{job_id}] Erro ao salvar no Redis: {e}")
        # Não é crítico, então não propagar o erro