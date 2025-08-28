import aiofiles
import uuid
from pathlib import Path
from app.modal_worker import run_modal_task

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

async def process_audio_job(file):
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"

    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    await run_modal_task(str(file_path))
    return {"job_id": file_id, "status": "sent_to_modal"}
