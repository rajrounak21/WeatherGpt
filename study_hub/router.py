from fastapi import APIRouter, HTTPException
from .service import load_topics, get_topic
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv(override=True)

router = APIRouter(prefix="/api/study", tags=["study"])

@router.get("/topics")
def topics():
    ts = load_topics()
    return {"topics": [t.model_dump() for t in ts]}

@router.get("/topic/{topic_id}")
def topic(topic_id: str):
    t = get_topic(topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="Topic not found")
    return t.model_dump()

@router.get("/quiz/{topic_id}")
def quiz(topic_id: str):
    t = get_topic(topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="Topic not found")
    return {"topic_id": topic_id, "quiz": [q.model_dump() for q in t.quiz]}

class ExplainReq(BaseModel):
    topic_id: str
    question: str
    mode: str = "simple"

@router.post("/explain")
def explain(req: ExplainReq):
    t = get_topic(req.topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="Topic not found")
    # Try Groq teacher mode, fallback to static
    try:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("no key")
        client = Groq(api_key=api_key)
        prompt = f"Explain for a beginner learning weather. Topic: {t.title}. Question: {req.question}. Mode: {req.mode}. Be supportive, give simple why and a weather connection. Plain text only, no markdown, no * or # or bullet dashes."
        resp = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}], max_tokens=300, temperature=0.7)
        text = (resp.choices[0].message.content or "").strip()
        # strip any markdown stars/bullets
        import re
        text = text.replace("**","").replace("*","").replace("##","")
        # remove leading dash bullets like "- Why? Warm..." -> "Why? Warm..."
        text = re.sub(r"^\s*-\s*", "", text, flags=re.MULTILINE)
        text = text.strip()
        if text:
            return {"answer": text}
    except Exception:
        pass
    # fallback
    fallback = {
        "simple": "Warm air is less dense, so it rises above cooler air. That's why thunderstorms can form.",
        "example": "Think of a hot air balloon — warm air inside is lighter and lifts.",
        "default": "Warm, moist air rises and helps create the conditions for weather events like thunderstorms."
    }
    return {"answer": fallback.get(req.mode, fallback["default"])}

class SubmitReq(BaseModel):
    topic_id: str
    answers: dict  # {question_id: selected_index}

@router.post("/quiz/submit")
def submit(req: SubmitReq):
    t = get_topic(req.topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="Topic not found")
    correct = 0
    details = []
    for q in t.quiz:
        sel = req.answers.get(q.id)
        is_correct = sel == q.correct
        if is_correct:
            correct += 1
        details.append({"id": q.id, "selected": sel, "correct": q.correct, "is_correct": is_correct, "why": q.why, "misconception": q.misconception})
    return {"total": len(t.quiz), "correct": correct, "details": details}

@router.post("/quiz/practice-again")
def practice_again(req: ExplainReq):
    # Generate one new question about same concept via Groq, fallback static structured
    import json as _json, re
    fallback = {"text": "What happens when warmer, less-dense air meets cooler, denser air?", "options": ["It sinks below the cooler air", "It rises above the cooler air", "It stops moving", "It turns into snow"], "correct": 1, "why": "Less-dense warm air rises above cooler, denser air."}
    def _parse(txt: str):
        if not txt:
            return None
        # Groq is prompted to return ONLY JSON — extract the JSON object cleanly
        m = re.search(r"\{[\s\S]*\}", txt)
        if not m:
            return None
        raw = m.group(0)
        # Groq sometimes uses ' instead of " — normalize once
        try:
            return _json.loads(raw)
        except Exception:
            try:
                return _json.loads(raw.replace("'", '"'))
            except Exception:
                return None

    try:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            client = Groq(api_key=api_key)
            resp = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content": f"Create one new beginner quiz question about {req.topic_id} weather, same concept as: '{req.question}'. Return ONLY valid JSON with keys text (string), options (4 strings), correct (0-3), why (string). No markdown."}], max_tokens=350, temperature=0.8)
            txt = (resp.choices[0].message.content or "").strip()
            parsed = _parse(txt)
            if parsed:
                return {"question": parsed}
            if txt and len(txt) < 600 and "{" not in txt:
                return {"question": {"text": txt.replace("**","").replace("*","").strip(), "options": fallback["options"], "correct": fallback["correct"], "why": fallback["why"]}}
    except Exception:
        pass
    return {"question": fallback}
