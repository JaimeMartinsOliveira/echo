import os
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class TriggerClient:
    def __init__(self):
        self.api_key = os.getenv("TRIGGER_SECRET_KEY")
        if not self.api_key:
            raise ValueError("A variável de ambiente TRIGGER_SECRET_KEY não está definida")

        self.base_url = os.getenv("TRIGGER_API_URL", "https://api.trigger.dev")
        self.task_id = os.getenv("TRIGGER_TASK_ID", "transcribe-audio")

        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

    async def _handle_error(self, e: httpx.HTTPError, context: str) -> None:
        """Loga e formata erro HTTP do Trigger.dev"""
        status_code = getattr(e.response, "status_code", "desconhecido")
        try:
            error_json = e.response.json()
        except Exception:
            error_json = e.response.text if e.response else "sem resposta"

        logger.error(f"[Trigger.dev] Erro em {context} | Status: {status_code} | Detalhes: {error_json}")
        raise Exception(f"Erro Trigger.dev em {context}: Status={status_code}, Detalhes={error_json}")

    async def create_transcription_job(
        self,
        job_id: str,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        language: str = "auto",
        webhook_url: Optional[str] = None
    ) -> str:
        """Cria um job de transcrição no Trigger.dev"""

        if not (file_path or file_url):
            raise ValueError("É necessário fornecer file_path ou file_url")

        payload: Dict[str, Any] = {
            "job_id": job_id,
            "language": language,
            "webhook_url": webhook_url or f"{os.getenv('APP_URL')}/webhooks/transcription"
        }
        if file_path:
            payload["file_path"] = file_path
        if file_url:
            payload["file_url"] = file_url

        try:
            response = await self.client.post(
                f"{self.base_url}/v4/tasks/{self.task_id}/run",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result.get("id", "")
        except httpx.HTTPError as e:
            await self._handle_error(e, "create_transcription_job")

    async def get_job_status(self, trigger_job_id: str) -> Dict[str, Any]:
        """Consulta status de um job pelo ID do Trigger.dev"""
        try:
            response = await self.client.get(f"{self.base_url}/v4/runs/{trigger_job_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            await self._handle_error(e, f"get_job_status({trigger_job_id})")

    async def cancel_job(self, trigger_job_id: str) -> bool:
        """Cancela um job em execução"""
        try:
            response = await self.client.post(f"{self.base_url}/v4/runs/{trigger_job_id}/cancel")
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            await self._handle_error(e, f"cancel_job({trigger_job_id})")
            return False

    async def get_job_status_by_job_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Consulta status de job pelo job_id do seu sistema (se você armazenar esse mapeamento)"""
        try:
            # Aqui você pode implementar lógica para buscar no seu DB/local mapping
            return None
        except Exception as e:
            logger.error(f"Erro ao consultar job por job_id {job_id}: {str(e)}")
            return None

    async def close(self):
        """Fecha o cliente HTTP"""
        await self.client.aclose()
