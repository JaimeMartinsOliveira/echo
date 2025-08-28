import whisperx

def run_worker(file_path: str):
    model = whisperx.load_model("small", device="cpu")
    audio = whisperx.load_audio(file_path)
    result = model.transcribe(audio)
    return result
