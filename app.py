from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from src.api.routes import upload, transcription, webhooks
from src.services.trigger_client import TriggerClient
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar conexões
    trigger_client = TriggerClient()
    app.state.trigger_client = trigger_client
    yield
    # Cleanup

app = FastAPI(
    title="Transcription API",
    description="API para transcrição de áudio/vídeo usando WhisperX",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(transcription.router, prefix="/api/v1", tags=["transcription"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

@app.get("/")
async def root():
    return {"message": "Transcription API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )