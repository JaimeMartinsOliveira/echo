import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
import json

logger = logging.getLogger(__name__)


class TriggerClient:
    def __init__(self):
        self.api_key = os.getenv("TRIGGER_SECRET_KEY")
        self.project_id = os.getenv("TRIGGER_PROJECT_ID")

        if not self.api_key:
            raise ValueError("TRIGGER_SECRET_KEY não está definida")
        if not self.project_id:
            raise ValueError("TRIGGER_PROJECT_ID não está definida")

        self.base_url = "https://api.trigger.dev"
        self.task_id = "transcribe-audio"

        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Echo-Transcription/1.0"
            },
            timeout=30.0
        )

    async def _handle_error(self, e: httpx.HTTPError, context: str) -> None:
        """Loga e formata erro HTTP do Trigger.dev"""
        status_code = getattr(e.response, "status_code", "desconhecido")
        try:
            error_text = e.response.text if e.response else "sem resposta"
        except Exception:
            error_text = "erro ao ler resposta"

        logger.error(f"[Trigger.dev] Erro em {context} | Status: {status_code} | Detalhes: {error_text}")
        raise Exception(f"Erro Trigger.dev em {context}: Status={status_code}")

    async def create_transcription_job(
            self,
            job_id: str,
            file_path: Optional[str] = None,
            file_url: Optional[str] = None,
            language: str = "auto",
            webhook_url: Optional[str] = None
    ) -> str:

        final_webhook_url = webhook_url or f"{os.getenv('APP_URL')}/webhooks/transcription"

        if not (file_path or file_url):
            raise ValueError("É necessário fornecer file_path ou file_url")

        payload: Dict[str, Any] = {
            "job_id": job_id,
            "language": language,
            "webhook_url": final_webhook_url
        }

        if file_path:
            app_url = os.getenv("APP_URL")
            if not app_url:
                raise ValueError("APP_URL não está configurada para construir a URL do ficheiro de upload")

            filename = Path(file_path).name

            public_file_url = f"{app_url}/uploads/{filename}"
            payload["file_url"] = public_file_url
        else:
            payload["file_url"] = file_url

        url = f"{self.base_url}/api/v1/tasks/{self.task_id}/trigger"

        body = {
            "payload": payload
        }

        logger.info(f"Enviando para Trigger.dev. URL: {url}, Payload para o worker: {payload}")

        try:
            response = await self.client.post(url, json=body)
            response.raise_for_status()
            result = response.json()
            trigger_job_id = result.get("id")
            if not trigger_job_id:
                raise Exception("Trigger.dev não retornou um ID de run")
            return trigger_job_id
        except httpx.HTTPError as e:
            status_code = getattr(e.response, "status_code", "desconhecido")
            error_text = e.response.text if e.response else "sem resposta"
            logger.error(f"[Trigger.dev] Erro | Status: {status_code} | Detalhes: {error_text}")
            raise Exception(f"Erro Trigger.dev: Status={status_code}")

    async def get_job_status(self, trigger_job_id: str) -> Dict[str, Any]:
        """Consulta status de um job pelo ID do Trigger.dev"""
        url = f"{self.base_url}/api/v1/runs/{trigger_job_id}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            await self._handle_error(e, f"get_job_status({trigger_job_id})")
            return {}

    async def cancel_job(self, trigger_job_id: str) -> bool:
        """Cancela um job em execução"""
        url = f"{self.base_url}/api/v1/runs/{trigger_job_id}/cancel"

        try:
            response = await self.client.post(url)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            await self._handle_error(e, f"cancel_job({trigger_job_id})")
            return False

    async def test_connection(self) -> bool:
        """Testa conexão com Trigger.dev"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/whoami")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False

    async def list_tasks(self) -> Dict[str, Any]:
        """Lista tasks disponíveis"""
        url = f"{self.base_url}/api/v1/tasks"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            await self._handle_error(e, "list_tasks")
            return {}

    async def close(self):
        """Fecha o cliente HTTP"""
        await self.client.aclose()
