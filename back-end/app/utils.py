import os
from fastapi import UploadFile


TEMP_DIR = os.getenv('TEMP_DIR', '/tmp/echo')
os.makedirs(TEMP_DIR, exist_ok=True)




def save_temp_file(upload_file: UploadFile, filename: str) -> str:
path = os.path.join(TEMP_DIR, filename)
with open(path, 'wb') as f:
f.write(upload_file.file.read())
return path




def save_result_to_storage(file_id: str, payload: dict):
# exemplo simples: salvar json em disco (para dev)
import json
path = os.path.join(TEMP_DIR, f"{file_id}_result.json")
with open(path, 'w', encoding='utf-8') as f:
json.dump(payload, f, ensure_ascii=False, indent=2)
return path