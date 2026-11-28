"""Voice -> Text via Groq Whisper"""

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv(override=True)

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe(file_path: str, language: str | None = None) -> str:
    """Transcribe audio file (wav/mp3/m4a) to text. language: 'hi' or 'en' or None auto."""
    with open(file_path, "rb") as f:
        kwargs = {"model": "whisper-large-v3-turbo", "file": (file_path, f.read())}
        if language:
            kwargs["language"] = language
        result = _client.audio.transcriptions.create(**kwargs)
    return result.text

def transcribe_bytes(audio_bytes: bytes, filename: str = "audio.wav", language: str | None = None) -> str:
    result = _client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=(filename, audio_bytes),
        **({"language": language} if language else {})
    )
    return result.text
