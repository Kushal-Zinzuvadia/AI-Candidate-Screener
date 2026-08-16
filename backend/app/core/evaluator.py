"""
Answer evaluator: scores a candidate's answer 0-5 via LLM.

Same JSON validation pattern as question_generator: validate, retry once,
fall back to a neutral score (3) so the interview never 500s.
"""
import json
import logging
import re

from pydantic import BaseModel, ValidationError

from app.core.llm_client import call_llm

logger = logging.getLogger(__name__)


class EvaluationResult(BaseModel):
    score: int   # 0–5
    feedback: str


_SYSTEM_PROMPT = """\
You are evaluating a candidate's answer to a technical interview question.

Scoring rubric:
  0 — No answer or completely off-topic
  1 — Major misconceptions; fundamentally wrong
  2 — Partially correct but significant gaps or errors
  3 — Mostly correct with minor gaps
  4 — Correct and complete
  5 — Excellent — demonstrates deep understanding or additional insight

Respond ONLY as valid JSON:
{"score": integer 0-5, "feedback": "1-2 sentence explanation"}"""

_USER_PROMPT = """\
Role: {role_name}
Topic: {topic}
Question: {question}
Candidate's Answer: {answer}
"""


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return json.loads(text)


def evaluate_answer(
    question: str,
    answer: str,
    topic: str,
    role_name: str,
) -> EvaluationResult:
    """Score the candidate's answer. Falls back to score=3 if LLM fails."""
    user = _USER_PROMPT.format(
        role_name=role_name, topic=topic, question=question, answer=answer[:2000]
    )

    for attempt in range(2):
        try:
            raw = call_llm(_SYSTEM_PROMPT, user, max_tokens=300)
            data = _parse_json(raw)
            result = EvaluationResult(**data)
            # Clamp score to valid range
            result.score = max(0, min(5, result.score))
            return result
        except (json.JSONDecodeError, ValidationError, Exception) as exc:
            logger.warning("Evaluation attempt %d failed: %s", attempt + 1, exc)

    logger.error("Evaluation failed — returning neutral fallback score.")
    return EvaluationResult(
        score=3,
        feedback="Evaluation could not be completed automatically.",
    )
