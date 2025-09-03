# ARQUIVO: src/services/url_downloader.py
# CRIAR ESTE ARQUIVO - ele não existe ainda
import os
import tempfile
import yt_dlp
import aiohttp
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class URLDownloader:
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "transcription_downloads"
        self.temp_dir.mkdir(exist_ok=True)

    async def download_from_url(self, url: str, job_id: str) -> str:
        """Download de áudio/vídeo de URL"""

        # Primeiro tenta download direto (para arquivos simples)
        if await self._is_direct_media_url(url):
            return await self._download_direct(url, job_id)

        # Se não for URL direta, usa yt-dlp (YouTube, etc.)
        return await self._download_with_ytdlp(url, job_id)

    async def _is_direct_media_url(self, url: str) -> bool:
        """Verifica se é URL direta para arquivo de mídia"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as response:
                    content_type = response.headers.get('Content-Type', '')
                    return content_type.startswith(('audio/', 'video/'))
        except:
            return False

    async def _download_direct(self, url: str, job_id: str) -> str:
        """Download direto de arquivo de mídia"""
        try:
            output_path = self.temp_dir / f"{job_id}_direct_download"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()

                    # Determinar extensão baseada no Content-Type
                    content_type = response.headers.get('Content-Type', '')
                    extension = self._get_extension_from_mime(content_type)
                    final_path = output_path.with_suffix(extension)

                    with open(final_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

            return str(final_path)

        except Exception as e:
            logger.error(f"Erro no download direto: {e}")
            raise Exception(f"Falha no download direto: {str(e)}")

    async def _download_with_ytdlp(self, url: str, job_id: str) -> str:
        """Download usando yt-dlp (YouTube, etc.)"""
        try:
            output_path = self.temp_dir / f"{job_id}.%(ext)s"

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(output_path),
                'extract_flat': False,
                'no_warnings': True,
                'quiet': True
            }

            # Executar download em thread separada para não bloquear
            import asyncio
            loop = asyncio.get_event_loop()

            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

            await loop.run_in_executor(None, download)

            # Encontrar arquivo baixado
            for file_path in self.temp_dir.glob(f"{job_id}.*"):
                if file_path.is_file():
                    return str(file_path)

            raise Exception("Arquivo baixado não encontrado")

        except Exception as e:
            logger.error(f"Erro no download com yt-dlp: {e}")
            raise Exception(f"Falha no download: {str(e)}")

    def _get_extension_from_mime(self, mime_type: str) -> str:
        """Converte MIME type para extensão de arquivo"""
        mime_to_ext = {
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg',
            'audio/flac': '.flac',
            'audio/aac': '.aac',
            'video/mp4': '.mp4',
            'video/webm': '.webm',
            'video/ogg': '.ogv'
        }
        return mime_to_ext.get(mime_type, '.tmp')

    async def cleanup_download(self, file_path: str) -> bool:
        """Remove arquivo baixado"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False