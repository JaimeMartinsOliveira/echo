# ARQUIVO: src/utils/validators.py
# CRIAR ESTE ARQUIVO - ele não existe ainda
import aiohttp
from fastapi import UploadFile
from typing import Dict, List
import magic
import os

# Formatos de áudio/vídeo suportados
SUPPORTED_AUDIO_FORMATS = {
    'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/wave',
    'audio/ogg', 'audio/flac', 'audio/aac', 'audio/mp4',
    'audio/x-m4a', 'audio/webm'
}

SUPPORTED_VIDEO_FORMATS = {
    'video/mp4', 'video/mpeg', 'video/quicktime',
    'video/x-msvideo', 'video/webm', 'video/ogg',
    'video/x-flv', 'video/3gpp'
}

SUPPORTED_FORMATS = SUPPORTED_AUDIO_FORMATS | SUPPORTED_VIDEO_FORMATS


async def validate_file(file: UploadFile) -> Dict[str, any]:
    """Valida arquivo de upload"""

    # Verificar tamanho
    max_size = int(os.getenv("MAX_FILE_SIZE", 500 * 1024 * 1024))  # 500MB
    file_size = 0
    content = await file.read()
    file_size = len(content)
    await file.seek(0)  # Reset file pointer

    if file_size > max_size:
        return {
            "valid": False,
            "message": f"Arquivo muito grande. Máximo: {max_size // (1024 * 1024)}MB"
        }

    if file_size == 0:
        return {
            "valid": False,
            "message": "Arquivo vazio"
        }

    # Verificar tipo MIME
    try:
        file_content = await file.read(1024)  # Lê apenas os primeiros 1024 bytes
        await file.seek(0)  # Reset file pointer

        mime_type = magic.from_buffer(file_content, mime=True)

        if mime_type not in SUPPORTED_FORMATS:
            return {
                "valid": False,
                "message": f"Formato não suportado: {mime_type}. Suportados: áudio e vídeo"
            }

    except Exception as e:
        return {
            "valid": False,
            "message": f"Erro ao validar arquivo: {str(e)}"
        }

    return {
        "valid": True,
        "message": "Arquivo válido",
        "mime_type": mime_type,
        "size": file_size
    }


async def validate_url(url: str) -> bool:
    """Valida se URL é acessível"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=10) as response:
                return response.status == 200
    except Exception:
        return False


def validate_language_code(language: str) -> bool:
    """Valida código de idioma"""
    # Códigos ISO 639-1 mais comuns + 'auto'
    valid_codes = {
        'auto', 'en', 'es', 'fr', 'de', 'it', 'pt', 'ru',
        'ja', 'ko', 'zh', 'ar', 'hi', 'tr', 'pl', 'nl',
        'sv', 'da', 'no', 'fi', 'cs', 'sk', 'hu', 'ro',
        'bg', 'hr', 'sl', 'et', 'lv', 'lt', 'mt', 'el'
    }
    return language.lower() in valid_codes