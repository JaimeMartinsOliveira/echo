from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import json
from datetime import datetime
from ...models.transcription import TranscriptionResult, TranscriptionStatus
from ...services.trigger_client import TriggerClient
from ...api.middleware.auth import optional_auth
from ...database.connection import get_db
from ...database.models import Job

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/transcription/{job_id}", response_model=TranscriptionResult)
async def get_transcription_status(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(optional_auth)
):
    """Consulta o status e resultado de uma transcrição"""
    
    try:
        # Primeiro verificar Redis se disponível
        if hasattr(request.app.state, 'redis_client') and request.app.state.redis_client:
            cached_result = await get_from_redis_cache(request.app.state.redis_client, job_id)
            if cached_result:
                return cached_result
        
        # Consultar banco de dados (fonte da verdade)
        db_job = db.query(Job).filter(Job.id == job_id).first()
        
        if not db_job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
        
        # Mapear para modelo Pydantic
        result = TranscriptionResult(
            job_id=db_job.id,
            status=db_job.status,
            text=db_job.result_text,
            segments=db_job.result_segments,
            language=db_job.result_language,
            duration=float(db_job.duration) if db_job.duration else None,
            created_at=db_job.created_at,
            completed_at=db_job.completed_at,
            error_message=db_job.error_message,
            metadata=db_job.metadata or {}
        )
        
        # Salvar no Redis se concluído/falhou (resultado final)
        if db_job.status in [TranscriptionStatus.COMPLETED, TranscriptionStatus.FAILED]:
            if hasattr(request.app.state, 'redis_client') and request.app.state.redis_client:
                await save_to_redis_cache(request.app.state.redis_client, job_id, result.dict())
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao consultar transcrição {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/transcription/{job_id}/download")
async def download_transcription(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db),
    format: str = Query(default="txt", description="Formato do download: txt, json, srt, vtt"),
    user: dict = Depends(optional_auth)
):
    """Download do resultado da transcrição em diferentes formatos"""
    
    try:
        # Buscar job no banco de dados
        db_job = db.query(Job).filter(Job.id == job_id).first()
        
        if not db_job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
        
        if db_job.status != TranscriptionStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail=f"Transcrição não concluída. Status atual: {db_job.status.value}"
            )
        
        if not db_job.result_text:
            raise HTTPException(status_code=404, detail="Resultado da transcrição não disponível")
        
        text = db_job.result_text
        segments = db_job.result_segments or []
        
        if format == "txt":
            content = text
            media_type = "text/plain"
            filename = f"transcription_{job_id}.txt"
            
        elif format == "json":
            content = json.dumps({
                "job_id": job_id,
                "text": text,
                "segments": segments,
                "language": db_job.result_language,
                "duration": db_job.duration,
                "created_at": db_job.created_at.isoformat() if db_job.created_at else None,
                "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None,
            }, indent=2, ensure_ascii=False)
            media_type = "application/json"
            filename = f"transcription_{job_id}.json"
            
        elif format == "srt":
            content = _convert_to_srt(segments)
            media_type = "text/plain"
            filename = f"transcription_{job_id}.srt"
            
        elif format == "vtt":
            content = _convert_to_vtt(segments)
            media_type = "text/plain"
            filename = f"transcription_{job_id}.vtt"
            
        else:
            raise HTTPException(status_code=400, detail="Formato não suportado. Use: txt, json, srt, vtt")
        
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao baixar transcrição {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.delete("/transcription/{job_id}")
async def cancel_transcription(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(optional_auth)
):
    """Cancela uma transcrição em andamento"""
    
    try:
        # Buscar job no banco de dados para obter trigger_job_id
        db_job = db.query(Job).filter(Job.id == job_id).first()
        
        if not db_job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
        
        # Verificar se pode ser cancelado
        if db_job.status in [TranscriptionStatus.COMPLETED, TranscriptionStatus.FAILED]:
            raise HTTPException(
                status_code=400, 
                detail=f"Job não pode ser cancelado. Status atual: {db_job.status.value}"
            )
        
        if not db_job.trigger_job_id:
            raise HTTPException(status_code=400, detail="Job não tem ID do Trigger associado")
        
        # Tentar cancelar no Trigger
        trigger_client = request.app.state.trigger_client
        success = await trigger_client.cancel_job(db_job.trigger_job_id)
        
        if success:
            # Atualizar status no banco de dados
            db_job.status = TranscriptionStatus.FAILED
            db_job.error_message = "Job cancelado pelo usuário"
            db_job.completed_at = datetime.utcnow()
            db_job.updated_at = datetime.utcnow()
            db.commit()
            
            return {"message": "Job cancelado com sucesso", "job_id": job_id}
        else:
            raise HTTPException(status_code=500, detail="Falha ao cancelar job no Trigger")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao cancelar job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/transcriptions")
async def list_transcriptions(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[TranscriptionStatus] = Query(default=None),
    db: Session = Depends(get_db),
    user: dict = Depends(optional_auth)
):
    """Lista transcrições do usuário"""
    
    try:
        # Construir query
        query = db.query(Job)
        
        # Filtrar por status se especificado
        if status:
            query = query.filter(Job.status == status)
        
        # Contar total
        total = query.count()
        
        # Aplicar paginação e ordenação
        jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
        
        # Converter para formato de resposta
        transcriptions = []
        for job in jobs:
            transcriptions.append({
                "job_id": job.id,
                "status": job.status.value,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "language": job.language,
                "file_url": job.file_url,
                "duration": job.duration,
                "has_text": bool(job.result_text),
                "error_message": job.error_message
            })
        
        return {
            "transcriptions": transcriptions,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar transcrições: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

# Funções auxiliares para Redis
async def get_from_redis_cache(redis_client, job_id: str) -> Optional[TranscriptionResult]:
    """Recupera resultado do cache Redis"""
    try:
        cached_data = await redis_client.get(f"job:{job_id}")
        if cached_data:
            data = json.loads(cached_data)
            return TranscriptionResult(**data)
        return None
    except Exception as e:
        logger.warning(f"Erro ao buscar no Redis: {e}")
        return None

async def save_to_redis_cache(redis_client, job_id: str, data: dict):
    """Salva resultado no cache Redis"""
    try:
        await redis_client.setex(
            f"job:{job_id}",
            86400,  # 24 horas
            json.dumps(data, default=str, ensure_ascii=False)
        )
    except Exception as e:
        logger.warning(f"Erro ao salvar no Redis: {e}")

# Funções de conversão (mantidas iguais)
def _convert_to_srt(segments: list) -> str:
    """Converte segmentos para formato SRT"""
    srt_content = []
    
    for i, segment in enumerate(segments, 1):
        start_time = _format_timestamp_srt(segment.get("start", 0))
        end_time = _format_timestamp_srt(segment.get("end", 0))
        text = segment.get("text", "").strip()
        
        srt_content.append(f"{i}")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(text)
        srt_content.append("")  # Linha vazia entre segmentos
    
    return "\n".join(srt_content)

def _convert_to_vtt(segments: list) -> str:
    """Converte segmentos para formato WebVTT"""
    vtt_content = ["WEBVTT", ""]
    
    for segment in segments:
        start_time = _format_timestamp_vtt(segment.get("start", 0))
        end_time = _format_timestamp_vtt(segment.get("end", 0))
        text = segment.get("text", "").strip()
        
        vtt_content.append(f"{start_time} --> {end_time}")
        vtt_content.append(text)
        vtt_content.append("")  # Linha vazia entre segmentos
    
    return "\n".join(vtt_content)

def _format_timestamp_srt(seconds: float) -> str:
    """Formata timestamp para formato SRT (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def _format_timestamp_vtt(seconds: float) -> str:
    """Formata timestamp para formato WebVTT (HH:MM:SS.mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"