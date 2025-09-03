from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi.responses import Response
from typing import Optional, List
import logging
import json
from datetime import datetime
from ...models.transcription import TranscriptionResult, TranscriptionStatus
from ...services.trigger_client import TriggerClient
from ...api.middleware.auth import optional_auth

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/transcription/{job_id}", response_model=TranscriptionResult)
async def get_transcription_status(
        job_id: str,
        request: Request,
        user: dict = Depends(optional_auth)
):
    """Consulta o status e resultado de uma transcrição"""

    try:
        # Aqui você consultaria seu banco de dados primeiro
        # Por enquanto, vamos consultar o Trigger diretamente

        trigger_client = request.app.state.trigger_client

        # Consultar status no Trigger
        trigger_status = await trigger_client.get_job_status_by_job_id(job_id)

        if not trigger_status:
            raise HTTPException(status_code=404, detail="Job não encontrado")

        # Mapear status do Trigger para nosso formato
        status_mapping = {
            "WAITING": TranscriptionStatus.PENDING,
            "EXECUTING": TranscriptionStatus.PROCESSING,
            "SUCCESS": TranscriptionStatus.COMPLETED,
            "FAILURE": TranscriptionStatus.FAILED,
            "CANCELLED": TranscriptionStatus.FAILED
        }

        status = status_mapping.get(trigger_status.get("status"), TranscriptionStatus.PENDING)

        # Criar datetime objects para as datas
        created_at = datetime.now()  # Você deve pegar do banco de dados
        completed_at = None
        if status == TranscriptionStatus.COMPLETED and trigger_status.get("completedAt"):
            completed_at = datetime.fromisoformat(trigger_status.get("completedAt").replace('Z', '+00:00'))

        result = TranscriptionResult(
            job_id=job_id,
            status=status,
            text=trigger_status.get("output", {}).get("text"),
            segments=trigger_status.get("output", {}).get("segments"),
            language=trigger_status.get("output", {}).get("language"),
            duration=trigger_status.get("output", {}).get("duration"),
            created_at=created_at,
            completed_at=completed_at,
            error_message=trigger_status.get("error"),
            metadata=trigger_status.get("metadata", {})
        )

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
        format: str = Query(default="txt", description="Formato do download: txt, json, srt, vtt"),
        user: dict = Depends(optional_auth)
):
    """Download do resultado da transcrição em diferentes formatos"""

    try:
        # Buscar resultado da transcrição
        trigger_client = request.app.state.trigger_client
        trigger_status = await trigger_client.get_job_status_by_job_id(job_id)

        if not trigger_status or trigger_status.get("status") != "SUCCESS":
            raise HTTPException(status_code=404, detail="Transcrição não encontrada ou não concluída")

        output = trigger_status.get("output", {})
        text = output.get("text", "")
        segments = output.get("segments", [])

        if format == "txt":
            content = text
            media_type = "text/plain"
            filename = f"transcription_{job_id}.txt"

        elif format == "json":
            content = json.dumps({
                "job_id": job_id,
                "text": text,
                "segments": segments,
                "language": output.get("language"),
                "duration": output.get("duration")
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
        user: dict = Depends(optional_auth)
):
    """Cancela uma transcrição em andamento"""

    try:
        trigger_client = request.app.state.trigger_client

        # Primeiro verificar se o job existe
        trigger_status = await trigger_client.get_job_status_by_job_id(job_id)
        if not trigger_status:
            raise HTTPException(status_code=404, detail="Job não encontrado")

        # Verificar se pode ser cancelado
        current_status = trigger_status.get("status")
        if current_status in ["SUCCESS", "FAILURE", "CANCELLED"]:
            raise HTTPException(
                status_code=400,
                detail=f"Job não pode ser cancelado. Status atual: {current_status}"
            )

        # Tentar cancelar
        trigger_job_id = trigger_status.get("id")
        success = await trigger_client.cancel_job(trigger_job_id)

        if success:
            return {"message": "Job cancelado com sucesso", "job_id": job_id}
        else:
            raise HTTPException(status_code=500, detail="Falha ao cancelar job")

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
        user: dict = Depends(optional_auth)
):
    """Lista transcrições do usuário"""

    try:
        # Aqui você implementaria a consulta no seu banco de dados
        # Por enquanto, retorna uma resposta mock

        transcriptions = [
            # Esta seria uma consulta real do banco de dados
            # Exemplo de estrutura de resposta:
        ]

        return {
            "transcriptions": transcriptions,
            "total": len(transcriptions),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Erro ao listar transcrições: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

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