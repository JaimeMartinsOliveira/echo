import os
from typing import Optional, Dict, Any
import httpx
import asyncio
from ..models.transcription import TranscriptionStatus

class TriggerClient:
    def __init__(self):
        self.api_key = os.getenv("TRIGGER_API_KEY")
        self.base_url = "https://api.trigger.dev"
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

    async def create_transcription_job(
            self,
            job_id: str,
            file_path: Optional[str] = None,
            file_url: Optional[str] = None,
            language: str = "auto",
            webhook_url: Optional[str] = None
    ) -> str:
        """Cria um job de transcrição no Trigger"""

        payload = {
            "job_id": job_id,
            "language": language,
            "webhook_url": webhook_url or f"{os.getenv('APP_URL')}/webhooks/transcription"
        }

        if file_path:
            payload["file_path"] = file_path
        elif file_url:
            payload["file_url"] = file_url
        else:
            raise ValueError("É necessário fornecer file_path ou file_url")

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/runs",
                json={
                    "task": "transcribe-audio",
                    "payload": payload
                }
            )
            response.raise_for_status()

            result = response.json()
            return result.get("id")

        except httpx.HTTPError as e:
            raise Exception(f"Erro ao criar job no Trigger: {str(e)}")

    async def get_job_status(self, trigger_job_id: str) -> Dict[str, Any]:
        """Consulta status de um job no Trigger"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/runs/{trigger_job_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise Exception(f"Erro ao consultar status do job: {str(e)}")

    async def cancel_job(self, trigger_job_id: str) -> bool:
        """Cancela um job no Trigger"""
        try:
            response = await self.client.post(f"{self.base_url}/api/v1/runs/{trigger_job_id}/cancel")
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def close(self):
        await self.client.aclose()

    async def get_job_status_by_job_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Consulta status de um job pelo job_id personalizado"""
        try:
            # Aqui você precisaria implementar uma busca por job_id personalizado
            # Isso pode requerer manter um mapeamento job_id -> trigger_job_id
            # Por enquanto, assumindo que você tem esse mapeamento em algum lugar
            
            # Em uma implementação real, você consultaria seu banco de dados:
            # trigger_job_id = await get_trigger_job_id_by_job_id(job_id)
            
            # Por enquanto, retorna None indicando que precisa ser implementado
            return None
            
        except Exception as e:
            logger.error(f"Erro ao consultar job por job_id {job_id}: {str(e)}")
            return None