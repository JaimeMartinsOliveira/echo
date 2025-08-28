import os
import requests


TRIGGER_ENDPOINT = os.getenv('TRIGGER_ENDPOINT') # ex: seu endpoint do Trigger.dev
TRIGGER_KEY = os.getenv('TRIGGER_KEY')


def trigger_job(file_id: str, filename: str):
"""Faz uma requisição para o Trigger.dev para começar o pipeline.
O Trigger pode então chamar o Modal para processar o arquivo.
"""
payload = {
"file_id": file_id,
"filename": filename,
}
headers = {"Authorization": f"Bearer {TRIGGER_KEY}"}
resp = requests.post(f"{TRIGGER_ENDPOINT}/start", json=payload, headers=headers, timeout=10)
resp.raise_for_status()
return resp.json()