import os
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class TriggerClient:
    def __init__(self):
        self.api_key = os.getenv("TRIGGER_SECRET_KEY")
        self.project_id = os.getenv("TRIGGER_PROJECT_ID")

        if not self.api_key:
            raise ValueError("TRIGGER_SECRET_KEY não está definida")
        if not self.project_id:
            raise ValueError("TRIGGER_PROJECT_ID não está definida")

        self.base_url = os.getenv("TRIGGER_API_URL", "https://api.trigger.dev")
        self.task_id = os.getenv("TRIGGER_TASK_ID", "transcribe-audio")

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
        """Cria um job de transcrição no Trigger.dev v4"""

        if not (file_path or file_url):
            raise ValueError("É necessário fornecer file_path ou file_url")

        # Payload para trigger
        payload: Dict[str, Any] = {
            "job_id": job_id,
            "language": language,
            "webhook_url": webhook_url or f"{os.getenv('APP_URL')}/webhooks/transcription"
        }

        if file_path:
            payload["file_path"] = file_path
        if file_url:
            payload["file_url"] = file_url

        # URL correta para v4 da API
        url = f"{self.base_url}/v2/projects/{self.project_id}/tasks/{self.task_id}/trigger"

        logger.info(f"Criando job no Trigger.dev: {url}")
        logger.debug(f"Payload: {payload}")

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            # A resposta deve conter um id do run
            trigger_job_id = result.get("id") or result.get("runId") or ""
            logger.info(f"Job criado com sucesso. Trigger ID: {trigger_job_id}")

            return trigger_job_id

        except httpx.HTTPError as e:
            await self._handle_error(e, "create_transcription_job")

    async def get_job_status(self, trigger_job_id: str) -> Dict[str, Any]:
        """Consulta status de um job pelo ID do Trigger.dev"""
        url = f"{self.base_url}/v2/projects/{self.project_id}/runs/{trigger_job_id}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            await self._handle_error(e, f"get_job_status({trigger_job_id})")

    async def cancel_job(self, trigger_job_id: str) -> bool:
        """Cancela um job em execução"""
        if self.base_url.startswith("http://localhost"):
            url = f"{self.base_url}/api/runs/{trigger_job_id}/cancel"
        else:
            url = f"{self.base_url}/v2/projects/{self.project_id}/runs/{trigger_job_id}/cancel"

        try:
            response = await self.client.post(url)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            await self._handle_error(e, f"cancel_job({trigger_job_id})")
            return False

    async def close(self):
        """Fecha o cliente HTTP"""
        await self.client.aclose()