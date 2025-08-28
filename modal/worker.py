quests
import whisperx


# Configs via env
MODAL_CALLBACK_URL = os.getenv('MODAL_CALLBACK_URL')
FILE_URL = os.getenv('FILE_URL') # onde o arquivo está hospedado (S3 / storage)
FILE_ID = os.getenv('FILE_ID')




def download_file(file_url: str, dest: str):
r = requests.get(file_url, stream=True)
r.raise_for_status()
with open(dest, 'wb') as f:
for chunk in r.iter_content(1024):
f.write(chunk)




def run_whisperx(path: str):
device = 'cuda' if whisperx.utils.get_device() == 'cuda' else 'cpu'
model = whisperx.load_model('small', device)
audio = whisperx.load_audio(path)
# transcribe + align + diarize (WhisperX integra pyannote internamente quando configurado)
result = whisperx.transcribe(model, audio)
return result




def post_result(payload: dict):
resp = requests.post(MODAL_CALLBACK_URL, json=payload, timeout=30)
resp.raise_for_status()
return resp.json()




if __name__ == '__main__':
# fluxo principal: baixar arquivo, processar, postar resultado
local_path = f"/tmp/{FILE_ID}.wav"
download_file(FILE_URL, local_path)
result = run_whisperx(local_path)


payload = {
'file_id': FILE_ID,
'transcript': result.get('text'),
'segments': result.get('segments'),
# adicione diarization/speakers se disponível
}
post_result(payload)