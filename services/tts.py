"""Text -> Voice via Groq Orpheus"""

import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv(override=True)

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Orpheus voices: autumn diana hannah austin daniel troy
VOICE_MAP = {"en": "autumn", "hinglish": "diana", "hi": "diana"}

def speak(text: str, lang: str = "en", out_path: str = "output.wav") -> str:
    """Generate wav file, return path. lang: en/hinglish/hi"""
    voice = VOICE_MAP.get(lang, "autumn")
    resp = _client.audio.speech.create(
        model="canopylabs/orpheus-v1-english",
        input=text,
        voice=voice,
        response_format="wav",
    )
    Path(out_path).write_bytes(resp.read())
    return out_path

def speak_bytes(text: str, lang: str = "en") -> bytes:
    voice = VOICE_MAP.get(lang, "autumn")
    resp = _client.audio.speech.create(
        model="canopylabs/orpheus-v1-english",
        input=text,
        voice=voice,
        response_format="wav",
    )
    return resp.read()
