import os
import aiofiles
from fastapi import UploadFile
from pathlib import Path
import uuid
from typing import Tuple

class FileHandler:
    def __init__(self):
        self.upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
        self.upload_dir.mkdir(exist_ok=True)
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", 500 * 1024 * 1024))  # 500MB default

    async def save_upload(self, file: UploadFile, job_id: str) -> str:
        """Salva arquivo de upload e retorna o caminho"""

        # Gerar nome único do arquivo
        file_extension = Path(file.filename).suffix
        filename = f"{job_id}{file_extension}"
        file_path = self.upload_dir / filename

        # Salvar arquivo
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        return str(file_path)

    async def delete_file(self, file_path: str) -> bool:
        """Remove arquivo do sistema"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    def get_file_info(self, file_path: str) -> dict:
        """Obtém informações do arquivo"""
        if not os.path.exists(file_path):
            return {}

        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime
        }