from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from src.api.routes import upload, transcription, webhooks
from src.services.trigger_client import TriggerClient
from src.database.connection import create_db_and_tables
import redis.asyncio as redis
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar banco de dados
    create_db_and_tables()
    print("✅ Database initialized")
    
    # Inicializar conexões
    trigger_client = TriggerClient()
    app.state.trigger_client = trigger_client
    
    # Inicializar Redis (opcional)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await redis_client.ping()
        app.state.redis_client = redis_client
        print("✅ Redis connected")
    except Exception as e:
        print(f"⚠️ Redis not available: {e}")
        app.state.redis_client = None
    
    yield
    
    # Cleanup
    if hasattr(app.state, 'redis_client') and app.state.redis_client:
        await app.state.redis_client.aclose()
    await trigger_client.close()

app = FastAPI(
    title="Echo - Transcription API",
    description="API para transcrição de áudio/vídeo usando WhisperX",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

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
    return {"message": "Echo Transcription API is running"}

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