from typing import Any, Optional
from pydantic import BaseModel


# ── Resume ────────────────────────────────────────────────────────────────────

class ResumeParsedResponse(BaseModel):
    resume_id: int
    candidate_id: int
    parsed_skills: list[str]
    parsed_technologies: list[str]
    profile_summary: str


# ── Roles ─────────────────────────────────────────────────────────────────────

class RoleOut(BaseModel):
    id: int
    name: str
    description: str
    kb_ready: bool  # True if ChromaDB collection exists and has documents

    model_config = {"from_attributes": True}


# ── Interview ─────────────────────────────────────────────────────────────────

class QuestionOut(BaseModel):
    id: int
    text: str
    topic: str
    difficulty: str
    order_index: int
    total_questions: int


class InterviewStartRequest(BaseModel):
    resume_id: int
    role_id: int


class InterviewStartResponse(BaseModel):
    session_id: int
    status: str
    question: QuestionOut


class CurrentQuestionResponse(BaseModel):
    session_id: int
    status: str
    question: Optional[QuestionOut] = None


class AnswerSubmitRequest(BaseModel):
    answer_text: str


class AnswerSubmitResponse(BaseModel):
    eval_score: int
    eval_feedback: str
    next_question: Optional[QuestionOut] = None
    status: str  # in_progress | completed


# ── Summary / Report ──────────────────────────────────────────────────────────

class TranscriptItem(BaseModel):
    order_index: int
    question: str
    topic: str
    difficulty: str
    answer: str
    score: int
    feedback: str
    source_chunk_ids: list[str]
    rationale: Optional[str] = None


class SummaryResponse(BaseModel):
    session_id: int
    overall_score: float
    strengths: list[Any]
    gaps: list[Any]
    summary_text: str
    transcript: list[TranscriptItem]
