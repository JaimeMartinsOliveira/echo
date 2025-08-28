from fastapi import APIRouter, UploadFile, BackgroundTasks
from app.jobs import process_audio_job

router = APIRouter()

@router.post("/upload-audio/")
async def upload_audio(file: UploadFile, background_tasks: BackgroundTasks):
    """
    Recebe um áudio e dispara job no Modal/Trigger
    """
    background_tasks.add_task(process_audio_job, file)
    return {"status": "processing", "filename": file.filename}
