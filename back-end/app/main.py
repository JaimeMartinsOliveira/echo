from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import shutil
import uuid
import os

# Placeholder para integração com Trigger.dev
def trigger_event(event_name: str, payload: dict):
    print(f"[Trigger] Evento: {event_name}, Payload: {payload}")

app = FastAPI(title="Echo API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload/")
async def upload_audio(file: UploadFile = File(...)):
    try:
        # gera nome único
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")

        # salva localmente
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # dispara evento para o Trigger.dev
        trigger_event("audio.uploaded", {"file_path": file_path, "file_id": file_id})

        return JSONResponse(content={
            "status": "success",
            "file_id": file_id,
            "file_path": file_path
        })

    except Exception as e:
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)


@app.get("/")
def healthcheck():
    return {"message": "Echo API is running 🚀"}
