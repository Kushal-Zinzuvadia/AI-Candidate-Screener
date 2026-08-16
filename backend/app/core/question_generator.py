"""
Question generator (§8): builds the LLM prompt from retrieved chunks + session
history, validates JSON output against a Pydantic schema, retries once on
failure, then falls back to a safe template question so the interview never 500s.
"""
import json
import logging
import re
from typing import Optional

from pydantic import BaseModel, ValidationError

from app.core.llm_client import call_llm

logger = logging.getLogger(__name__)


# ── Output schema ─────────────────────────────────────────────────────────────

class GeneratedQuestion(BaseModel):
    question: str
    topic: str
    difficulty: str  # easy | medium | hard
    source_chunk_ids: list[str]
    rationale: str


# ── Prompt templates ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are conducting a technical interview for the role of {role_name}.
Ask exactly one question, grounded ONLY in the provided context chunks.
Do not introduce facts, terms, or examples not present in the context or the candidate's resume.
Calibrate depth to the candidate's apparent experience and to their performance so far.

IMPORTANT CONSTRAINTS:
- Do NOT reference any books, chapters, textbooks, course materials, papers, or source documents.
- Do NOT use phrases like "as described in", "according to", "in chapter X", "as mentioned in the context".
- Ask questions that test practical understanding, real-world reasoning, and conceptual depth — not recall of specific text.
- Frame questions as if you are a senior engineer asking a colleague, not a professor testing a student's reading.

Respond ONLY as valid JSON matching this schema exactly:
{{
  "question": string,
  "topic": string,
  "difficulty": "easy" | "medium" | "hard",
  "source_chunk_ids": [string],
  "rationale": string
}}"""

_USER_PROMPT = """\
Role: {role_name}
Candidate profile: {profile_summary}
Candidate skills: {skill_list}

Retrieved context (ground your question in these chunks only):
{context_blocks}

Interview history so far:
{history_block}

Instructions:
- If the previous answer scored 4-5: go deeper on the same topic or raise difficulty.
- If it scored 1-2: pivot to a simpler foundational topic from the context.
- Reference which chunk IDs informed this question in source_chunk_ids.
- The rationale field is internal — do not show it to the candidate.
"""

_STRICT_REMINDER = """Your previous response was not valid JSON. Reply ONLY with the JSON object and nothing else."""

_FALLBACK_QUESTION = GeneratedQuestion(
    question="Can you walk me through how you would approach designing a system you've worked on recently, focusing on the trade-offs you made?",
    topic="general system design",
    difficulty="medium",
    source_chunk_ids=[],
    rationale="Fallback question used when question generation failed.",
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(no retrieved context — ask a general role-relevant question)"
    lines = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source_title", "knowledge base")
        section = meta.get("section", "")
        label = f"[C{i}] ({source}" + (f", {section}" if section else "") + f") [id={chunk['chunk_id']}]"
        lines.append(f"{label}:\n{chunk['text'][:600]}")
    return "\n\n".join(lines)


def _format_history(session_history: list[dict]) -> str:
    if not session_history:
        return "(first question — no history)"
    lines = []
    for i, h in enumerate(session_history, 1):
        lines.append(f"Q{i}: {h['question']} | Answer: {h['answer'][:200]} | Score: {h['score']}/5")
    return "\n".join(lines)


def _parse_json(text: str) -> dict:
    """Strip markdown fences and parse JSON."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return json.loads(text)


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_question(
    role_name: str,
    profile_summary: str,
    skills: list[str],
    technologies: list[str],
    chunks: list[dict],
    session_history: list[dict],  # [{question, answer, score, topic}]
    retrieval_query: str = "",
) -> GeneratedQuestion:
    """
    Generate one question. Validates with Pydantic; retries once on failure;
    falls back to _FALLBACK_QUESTION if both attempts fail.
    """
    system = _SYSTEM_PROMPT.format(role_name=role_name)
    user = _USER_PROMPT.format(
        role_name=role_name,
        profile_summary=profile_summary or "Not provided",
        skill_list=", ".join(skills + technologies) or "Not specified",
        context_blocks=_format_context(chunks),
        history_block=_format_history(session_history),
    )

    for attempt in range(2):
        try:
            if attempt == 1:
                user = user + "\n\n" + _STRICT_REMINDER
            raw = call_llm(system, user, max_tokens=700)
            data = _parse_json(raw)
            return GeneratedQuestion(**data)
        except (json.JSONDecodeError, ValidationError, Exception) as exc:
            logger.warning("Question generation attempt %d failed: %s", attempt + 1, exc)

    logger.error("Both question generation attempts failed — using fallback question.")
    return _FALLBACK_QUESTION
