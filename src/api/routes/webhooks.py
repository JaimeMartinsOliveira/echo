from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/transcription")
async def transcription_webhook(request: Request):
    """Recebe notificações de status dos jobs de transcrição"""

    try:
        payload = await request.json()
        job_id = payload.get("job_id")
        status = payload.get("status")

        logger.info(f"Webhook recebido para job {job_id}: {status}")

        # Aqui você pode:
        # 1. Atualizar banco de dados
        # 2. Notificar cliente via WebSocket
        # 3. Enviar email/notificação push
        # 4. Limpar arquivos temporários se concluído

        if status == "completed":
            # Processar resultado da transcrição
            text = payload.get("text")
            segments = payload.get("segments")
            language = payload.get("language")

            # Salvar no banco/cache
            await save_transcription_result(job_id, {
                "text": text,
                "segments": segments,
                "language": language,
                "status": status
            })

            # Limpar arquivo se necessário
            # await cleanup_job_files(job_id)

        elif status == "failed":
            error_message = payload.get("error_message")
            logger.error(f"Job {job_id} falhou: {error_message}")

            # Atualizar status de erro
            await save_transcription_result(job_id, {
                "status": status,
                "error_message": error_message
            })

        return JSONResponse(
            status_code=200,
            content={"message": "Webhook processado com sucesso"}
        )

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno")

async def save_transcription_result(job_id: str, result: dict):
    """Salva resultado da transcrição (implementar conforme seu banco de dados)"""
    # Implementar salvamento no banco de dados
    # Exemplo com Redis/MongoDB/PostgreSQL
    pass