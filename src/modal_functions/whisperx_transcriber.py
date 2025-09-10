import modal
import os
from typing import Optional, Dict, Any
import whisperx
import torch
import tempfile
import httpx
from pathlib import Path

app = modal.App("whisperx-transcriber")

image = modal.Image.debian_slim().pip_install([
    "whisperx",
    "torch",
    "torchaudio",
    "ffmpeg-python",
    "httpx",
    "yt-dlp==2025.7.21",
    "fastapi"
]).apt_install([
    "ffmpeg"
])

youtube_cookies = modal.Secret.from_name("youtube-cookies")


@app.function(
    image=image,
    gpu="T4",
    memory=8192,
    timeout=1800,
    retries=3,
    secrets=[youtube_cookies]
)
def transcribe_gpu_worker(
        job_id: str,
        file_url: Optional[str] = None,
        file_path: Optional[str] = None,
        language: str = "auto",
        webhook_url: Optional[str] = None
):
    audio_file = None
    try:
        if webhook_url:
            notify_webhook(webhook_url, job_id, "processing", "Iniciando transcrição na GPU")

        if file_path and os.path.exists(file_path):
            audio_file = file_path
        elif file_url:
            audio_file = download_audio_from_url(file_url, job_id, youtube_cookies)
        else:
            raise Exception("Nenhum arquivo ou URL válida fornecida")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "float32"

        model = whisperx.load_model("large-v2", device, compute_type=compute_type,
                                    language=None if language == "auto" else language)
        audio = whisperx.load_audio(audio_file)
        result = model.transcribe(audio, batch_size=16)
        detected_language = result.get("language", language)

        if detected_language != "auto":
            model_a, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

        transcription_result = {
            "job_id": job_id,
            "status": "completed",
            "text": " ".join([segment["text"] for segment in result["segments"]]),
            "segments": result["segments"],
            "language": detected_language,
            "duration": len(audio) / 16000,
        }

        if webhook_url:
            notify_webhook(webhook_url, job_id, "completed", "Transcrição concluída", transcription_result)

    except Exception as e:
        error_msg = str(e)
        if webhook_url:
            notify_webhook(webhook_url, job_id, "failed", error_msg)
    finally:
        if audio_file and os.path.exists(audio_file) and file_url:
            try:
                os.remove(audio_file)
            except OSError as e:
                print(f"Erro ao remover arquivo temporário {audio_file}: {e}")


@app.function(image=image)
@modal.fastapi_endpoint(method="POST")
def web_accept_job(payload: dict):
    job_id = payload.get("job_id")
    if not job_id:
        return {"error": "job_id é obrigatório no payload"}, 400

    transcribe_gpu_worker.spawn(
        job_id=job_id,
        file_url=payload.get("file_url"),
        file_path=payload.get("file_path"),
        language=payload.get("language"),
        webhook_url=payload.get("webhook_url")
    )

    return {"status": "transcription_queued", "job_id": job_id}, 202


def download_audio_from_url(url: str, job_id: str, cookies_secret: modal.Secret) -> str:
    import yt_dlp

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, f"{job_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(output_path),
        'extract_flat': False,
        'quiet': True,
    }

    cookie_file_path = None
    try:
        cookies_content = cookies_secret["COOKIES_TXT"]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=temp_dir, suffix='.txt') as temp_cookie_file:
            temp_cookie_file.write(cookies_content)
            cookie_file_path = temp_cookie_file.name

        ydl_opts['cookiefile'] = cookie_file_path

    except (KeyError, FileNotFoundError):
        print("Segredo 'youtube-cookies' ou chave 'COOKIES_TXT' não encontrados. A tentar sem cookies.")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if cookie_file_path and os.path.exists(cookie_file_path):
        os.remove(cookie_file_path)

    for file in os.listdir(temp_dir):
        if file.startswith(job_id):
            return os.path.join(temp_dir, file)

    raise Exception("Falha ao baixar arquivo da URL")


def notify_webhook(webhook_url: str, job_id: str, status: str, message: str, result: Optional[Dict, Any] = None):
    try:
        payload = {"job_id": job_id, "status": status, "message": message}
        if result:
            payload.update(result)
        with httpx.Client() as client:
            client.post(webhook_url, json=payload, timeout=30)
    except Exception as e:
        print(f"Erro ao notificar webhook: {e}")