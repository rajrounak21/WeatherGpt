import json
from pathlib import Path
from .schemas import Topic

_content_path = Path(__file__).parent / "content" / "topics.json"
_topics_cache = None

def load_topics() -> list[Topic]:
    global _topics_cache
    if _topics_cache is None:
        data = json.loads(_content_path.read_text(encoding="utf-8"))
        _topics_cache = [Topic(**t) for t in data]
    return _topics_cache

def get_topic(topic_id: str) -> Topic | None:
    for t in load_topics():
        if t.id == topic_id:
            return t
    return None
