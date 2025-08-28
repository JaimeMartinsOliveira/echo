from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from uuid import uuid4
import os
from app.jobs import trigger_job
from app.utils import save_temp_file


router = APIRouter()


@router.post('/process')
async def process_audio(file: UploadFile = File(...)):
# salva o arquivo localmente (ou envia para S3)
file_id = str(uuid4())
filename = f"{file_id}_{file.filename}"
path = save_temp_file(file, filename)


# dispara job no Trigger.dev (que orquestrará o Modal)
try:
job_resp = trigger_job(file_id=file_id, filename=filename)
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))


return {"file_id": file_id, "status": "queued", "trigger": job_resp}


# Endpoint que o Modal chamará quando terminar
@router.post('/modal/callback')
async def modal_callback(payload: dict):
# payload esperado: {"file_id": ..., "transcript": ..., "segments": ..., ...}
# aqui você pode salvar no DB, notificar websocket, etc.
# por enquanto só retorna OK
return {"received": True, "file_id": payload.get('file_id')}