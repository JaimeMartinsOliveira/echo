# ARQUIVO: src/utils/helpers.py
# CRIAR ESTE ARQUIVO - ele não existe ainda
import uuid
import os
from datetime import datetime
from typing import Optional
import hashlib


def generate_job_id() -> str:
    """Gera ID único para job"""
    return str(uuid.uuid4())


def estimate_transcription_time(file_size_bytes: int) -> int:
    """Estima tempo de transcrição baseado no tamanho do arquivo"""
    # Estimativa: ~1 minuto de processamento para cada 10MB
    estimated_minutes = max(1, file_size_bytes // (10 * 1024 * 1024))
    return estimated_minutes * 60  # retorna em segundos


def get_file_extension(filename: str) -> str:
    """Extrai extensão do arquivo"""
    return os.path.splitext(filename)[1].lower()


def format_duration(seconds: float) -> str:
    """Formata duração em formato legível"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def generate_file_hash(file_path: str) -> str:
    """Gera hash do arquivo para verificação de integridade"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def sanitize_filename(filename: str) -> str:
    """Remove caracteres problemáticos do nome do arquivo"""
    import re
    # Remove caracteres especiais
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # Substitui espaços por underscores
    filename = re.sub(r'[-\s]+', '_', filename)
    return filename.strip()


def format_file_size(size_bytes: int) -> str:
    """Formata tamanho do arquivo em formato legível"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"