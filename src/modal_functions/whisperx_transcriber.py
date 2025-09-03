import modal
import os
from typing import Optional, Dict, Any
import whisperx
import torch
import tempfile
import httpx
from pathlib import Path

# Configurar imagem Modal com dependências
image = modal.Image.debian_slim().pip_install([
    "whisperx",
    "torch",
    "torchaudio",
    "ffmpeg-python",
    "httpx",
    "yt-dlp"
]).apt_install([
    "ffmpeg"
])

app = modal.App("whisperx-transcriber")

@app.function(
    image=image,
    gpu=modal.gpu.T4(),  # GPU para melhor performance
    memory=8192,  # 8GB RAM
    timeout=1800,  # 30 minutos timeout
    mounts=[modal.Mount.from_local_dir(".", remote_path="/app")]
)
async def transcribe_audio(
        job_id: str,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        language: str = "auto",
        webhook_url: Optional[str] = None
) -> Dict[str, Any]:
    """Função principal de transcrição usando WhisperX"""

    try:
        # Notificar início do processamento
        if webhook_url:
            await notify_webhook(webhook_url, job_id, "processing", "Iniciando transcrição")

        # Preparar arquivo de áudio
        audio_file = None
        if file_path and os.path.exists(file_path):
            audio_file = file_path
        elif file_url:
            audio_file = await download_audio_from_url(file_url, job_id)
        else:
            raise Exception("Nenhum arquivo ou URL válida fornecida")

        # Configurar dispositivo
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"

        # Carregar modelo WhisperX
        model = whisperx.load_model(
            "large-v2",
            device=device,
            compute_type=compute_type,
            language=None if language == "auto" else language
        )

        # Carregar áudio
        audio = whisperx.load_audio(audio_file)

        # Transcrever
        result = model.transcribe(audio, batch_size=16)

        # Detectar idioma se não foi especificado
        detected_language = result.get("language", language)

        # Alinhamento (opcional, melhora precisão)
        if detected_language != "auto":
            model_a, metadata = whisperx.load_align_model(
                language_code=detected_language,
                device=device
            )
            result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                device,
                return_char_alignments=False
            )

        # Diarização (opcional, identificar falantes)
        # diarize_model = whisperx.DiarizationPipeline(use_auth_token="YOUR_HF_TOKEN", device=device)
        # diarize_segments = diarize_model(audio_file)
        # result = whisperx.assign_word_speakers(diarize_segments, result)

        # Preparar resultado final
        transcription_result = {
            "job_id": job_id,
            "status": "completed",
            "text": " ".join([segment["text"] for segment in result["segments"]]),
            "segments": result["segments"],
            "language": detected_language,
            "duration": len(audio) / 16000,  # WhisperX usa 16kHz
        }

        # Notificar conclusão
        if webhook_url:
            await notify_webhook(webhook_url, job_id, "completed", "Transcrição concluída", transcription_result)

        return transcription_result

    except Exception as e:
        error_msg = str(e)
        error_result = {
            "job_id": job_id,
            "status": "failed",
            "error_message": error_msg
        }

        # Notificar erro
        if webhook_url:
            await notify_webhook(webhook_url, job_id, "failed", error_msg)

        return error_result

    finally:
        # Cleanup de arquivos temporários
        if file_url and audio_file and os.path.exists(audio_file):
            os.remove(audio_file)

async def download_audio_from_url(url: str, job_id: str) -> str:
    """Download de áudio/vídeo de URL usando yt-dlp"""
    import yt_dlp

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, f"{job_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'extract_flat': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Encontrar arquivo baixado
    for file in os.listdir(temp_dir):
        if file.startswith(job_id):
            return os.path.join(temp_dir, file)

    raise Exception("Falha ao baixar arquivo da URL")

async def notify_webhook(
        webhook_url: str,
        job_id: str,
        status: str,
        message: str,
        result: Optional[Dict[str, Any]] = None
):
    """Notifica webhook sobre status do job"""
    try:
        payload = {
            "job_id": job_id,
            "status": status,
            "message": message
        }
        if result:
            payload.update(result)

        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=payload, timeout=30)
    except Exception as e:
        print(f"Erro ao notificar webhook: {e}")