from pydantic import BaseModel
from typing import Optional, List

class LessonSlide(BaseModel):
    title: str
    body: str
    visual: Optional[str] = None
    key_idea: Optional[str] = None

class Question(BaseModel):
    id: str
    text: str
    options: List[str]
    correct: int
    why: str
    misconception: Optional[str] = None

class Topic(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    lessons: List[LessonSlide]
    quiz: List[Question]

class TopicsResponse(BaseModel):
    topics: List[Topic]
