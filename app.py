"""Simple preview: Text + Voice WeatherGPT Agent"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

from agent.graph import ask
from services.stt import transcribe
from services.tts import speak

def detect_lang(text: str) -> str:
    hinglish_hints = ["kal", "aaj", "mausam", "garmi", "thand", "kaisa", "kya", "hai"]
    t = text.lower()
    if any(w in t for w in hinglish_hints):
        return "hinglish"
    return "en"

def chat_text(query: str, voice: bool = False):
    print(f"\nYou: {query}")
    answer = ask(query)
    print(f"Agent: {answer}")
    if voice:
        lang = detect_lang(query)
        out = speak(answer, lang=lang, out_path="output.wav")
        print(f"Voice: saved {out} ({lang})")
    return answer

if __name__ == "__main__":
    # CLI: python app.py "What is weather tomorrow in Kolkata?" --voice
    voice = "--voice" in sys.argv
    query = " ".join([a for a in sys.argv[1:] if a != "--voice"]) or "What is the weather tomorrow in Kolkata?"
    
    # optional: if file path passed and is wav, do STT
    if query.strip().endswith((".wav", ".mp3", ".m4a")):
        try:
            text = transcribe(query.strip())
            print(f"STT: {text}")
            query = text
        except Exception as e:
            print(f"STT failed: {e}")

    chat_text(query, voice=voice)
