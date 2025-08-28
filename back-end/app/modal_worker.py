import modal

stub = modal.Stub("echo-app")

@stub.function(image=modal.Image.debian_slim().pip_install("whisperx", "pyannote.audio"))
def transcribe_audio(file_path: str):
    """
    Worker que roda no Modal
    """
    import whisperx

    model = whisperx.load_model("small", device="cpu")
    audio = whisperx.load_audio(file_path)
    result = model.transcribe(audio)

    return result
