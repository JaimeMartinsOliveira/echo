import modal
import os
from typing import Optional, Dict, Any
import whisperx
import torch
import tempfile
import httpx
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = modal.App("whisperx-transcriber")


image = modal.Image.debian_slim().pip_install([
    "whisperx==3.4.2",
    "faster-whisper>=1.1.1",
    "torch>=2.5.1",
    "torchaudio>=2.5.1",
    "transformers>=4.48.0",
    "numpy>=2.0.2",
    "ffmpeg-python",
    "httpx",
    "fastapi"
]).apt_install([
    "ffmpeg"
])

@app.function(
    image=image,
    gpu="T4",
    memory=8192,
    timeout=1800,
    retries=3
)
def transcribe_gpu_worker(
        job_id: str,
        file_url: Optional[str] = None,
        language: str = "auto",
        webhook_url: Optional[str] = None
):
    audio_file = None
    try:
        logger.info(f"[{job_id}] Iniciando worker GPU.")
        if webhook_url:
            notify_webhook(webhook_url, job_id, "processing", "Iniciando transcrição na GPU")

        if not file_url:
            raise Exception("Nenhuma file_url foi fornecida para o worker")

        audio_file = download_direct_url(file_url, job_id)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "float32"

        model = whisperx.load_model("large-v2", device, compute_type=compute_type,
                                    language=None if language == "auto" else language)
        audio = whisperx.load_audio(audio_file)
        result = model.transcribe(audio, batch_size=16)
        detected_language = result.get("language", language)

        if detected_language and detected_language != "auto":
            model_a, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

        transcription_result = {
            "job_id": job_id, "status": "completed",
            "text": " ".join([segment["text"] for segment in result.get("segments", [])]),
            "segments": result.get("segments"), "language": detected_language,
            "duration": len(audio) / 16000 if audio is not None else 0,
        }

        if webhook_url:
            notify_webhook(webhook_url, job_id, "completed", "Transcrição concluída", transcription_result)

        return transcription_result

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{job_id}] Erro fatal na transcrição: {error_msg}", exc_info=True)
        if webhook_url:
            notify_webhook(webhook_url, job_id, "failed", error_msg)
        raise e
    finally:
        if audio_file and os.path.exists(audio_file):
            os.remove(audio_file)


@app.function(image=image)
@modal.fastapi_endpoint(method="POST")
def web_accept_job(payload: dict):
    job_id = payload.get("job_id")
    if not job_id:
        return {"error": "job_id é obrigatório no payload"}, 400

    transcribe_gpu_worker.spawn(
        job_id=job_id,
        file_url=payload.get("file_url"),
        language=payload.get("language", "auto"),
        webhook_url=payload.get("webhook_url")
    )

    return {"status": "transcription_queued", "job_id": job_id}, 202


def download_direct_url(url: str, job_id: str) -> str:
    temp_dir = tempfile.mkdtemp()
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=60) as response:
            response.raise_for_status()
            ext = Path(url).suffix or ".tmp"
            output_path = os.path.join(temp_dir, f"{job_id}{ext}")
            with open(output_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
            return output_path
    except Exception as e:
        raise Exception(f"Falha ao baixar ficheiro da URL {url}: {str(e)}")


def notify_webhook(webhook_url: str, job_id: str, status: str, message: str, result: Optional[Dict[str, Any]] = None):
    try:
        payload = {"job_id": job_id, "status": status, "message": message}
        if result:
            payload.update(result)
        with httpx.Client(timeout=30) as client:
            client.post(webhook_url, json=payload)
    except Exception as e:
        logger.error(f"[{job_id}] Erro ao notificar webhook: {e}")