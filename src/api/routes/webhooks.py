from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import json
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
        
        logger.info(f"Webhook recebido para job {job_id}: {status}")
        
        if not job_id:
            raise HTTPException(status_code=400, detail="job_id é obrigatório")
        
        # Buscar job no banco de dados
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if not db_job:
            logger.error(f"Job {job_id} não encontrado no banco de dados")
            raise HTTPException(status_code=404, detail="Job não encontrado")
        
        # Processar baseado no status
        if status == "completed":
            await save_transcription_result(db, db_job, payload)
            logger.info(f"Job {job_id} concluído com sucesso")
            
        elif status == "failed":
            await save_transcription_error(db, db_job, payload)
            logger.error(f"Job {job_id} falhou: {payload.get('error_message', 'Erro desconhecido')}")
            
        elif status == "processing":
            # Atualizar status para processing
            db_job.status = TranscriptionStatus.PROCESSING
            db_job.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"Job {job_id} em processamento")
        
        # Salvar no Redis se disponível
        if hasattr(request.app.state, 'redis_client') and request.app.state.redis_client:
            await save_to_redis_cache(request.app.state.redis_client, job_id, db_job.to_dict())
        
        return JSONResponse(
            status_code=200,
            content={"message": "Webhook processado com sucesso"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno")

async def save_transcription_result(db: Session, job: Job, payload: dict):
    """Salva resultado da transcrição concluída"""
    try:
        # Atualizar status e resultados
        job.status = TranscriptionStatus.COMPLETED
        job.result_text = payload.get("text")
        job.result_segments = payload.get("segments")
        job.result_language = payload.get("language")
        job.duration = str(payload.get("duration")) if payload.get("duration") else None
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        
        # Limpar mensagem de erro se existir
        job.error_message = None
        
        db.commit()
        
        # Opcional: Limpar arquivo temporário se for upload
        if job.file_path and os.path.exists(job.file_path):
            try:
                # Aguardar um pouco antes de limpar para garantir que o processamento terminou
                import asyncio
                await asyncio.sleep(5)
                from ...services.file_handler import FileHandler
                file_handler = FileHandler()
                await file_handler.delete_file(job.file_path)
                logger.info(f"Arquivo temporário removido: {job.file_path}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
                
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao salvar resultado da transcrição: {e}")
        raise

async def save_transcription_error(db: Session, job: Job, payload: dict):
    """Salva erro da transcrição"""
    try:
        job.status = TranscriptionStatus.FAILED
        job.error_message = payload.get("error_message", "Erro desconhecido durante a transcrição")
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Limpar arquivo temporário em caso de erro também
        if job.file_path and os.path.exists(job.file_path):
            try:
                from ...services.file_handler import FileHandler
                file_handler = FileHandler()
                await file_handler.delete_file(job.file_path)
                logger.info(f"Arquivo temporário removido após erro: {job.file_path}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário após falha: {e}")
                
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao salvar erro da transcrição: {e}")
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
        logger.debug(f"Job {job_id} salvo no cache Redis")
    except Exception as e:
        logger.warning(f"Erro ao salvar no Redis: {e}")
        # Não é crítico, então não propagar o erro