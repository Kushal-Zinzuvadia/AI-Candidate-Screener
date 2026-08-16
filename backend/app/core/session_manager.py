"""
Session manager (§9): orchestrates the interview state machine.

State transitions:
  created  ──(start_interview)──►  in_progress  ──(submit_answer, N==max)──►  completed
                                        │
                                        └──(submit_answer, N<max) ── loop

This module is the single coordinator — routes call it and it calls all
core modules (context_builder, rag_engine, question_generator, evaluator,
report_generator). Routes stay thin.
"""
import json
import logging
import re

from sqlalchemy.orm import Session

from app.config import settings
from app.core import context_builder, rag_engine, question_generator, evaluator
from app.core.llm_client import call_llm
from app.db import crud, models
from app.db.schemas import QuestionOut

logger = logging.getLogger(__name__)


# ── Report generation ──────────────────────────────────────────────────────────

_REPORT_SYSTEM = """\
You are summarizing a technical interview. Given the Q&A transcript and scores,
produce a JSON report with exactly this structure:
{
  "summary_text": string (2-3 sentences, overall performance narrative),
  "strengths": [
    {"area": string (short topic label, e.g. "Gradient Descent"), "detail": string (1-2 sentences of specific, actionable observation)},
    ... (2-3 items)
  ],
  "gaps": [
    {"area": string (short topic label), "detail": string (1-2 sentences describing the gap and what to study)},
    ... (2-3 items)
  ]
}

Rules:
- Be specific and evidence-based — cite what the candidate actually said or missed.
- Do NOT invent topics not present in the transcript.
- Do NOT reference books, chapters, or source materials.
- Strengths should highlight demonstrated understanding or clear articulation.
- Gaps should be constructive: name the concept and suggest what depth is missing."""


def _generate_report(
    db: Session,
    session: models.InterviewSession,
) -> models.Report:
    transcript_lines = []
    for q in session.questions:
        ans = q.answer
        score = ans.eval_score if ans else "N/A"
        answer_text = ans.answer_text[:300] if ans else "(no answer)"
        transcript_lines.append(
            f"Q{q.order_index} [{q.topic}]: {q.question_text}\n"
            f"Answer: {answer_text}\nScore: {score}/5"
        )

    overall = 0.0
    scored = [q.answer for q in session.questions if q.answer and q.answer.eval_score is not None]
    if scored:
        overall = round(sum(a.eval_score for a in scored) / len(scored), 2)

    user = (
        f"Role: {session.role.name}\n"
        f"Overall average score: {overall}/5\n\n"
        f"Transcript:\n" + "\n\n".join(transcript_lines)
    )

    report_data = {"summary_text": "", "strengths": [], "gaps": []}
    try:
        raw = call_llm(_REPORT_SYSTEM, user, max_tokens=1200)
        # Extract the JSON object from the response, ignoring any prose preamble
        # or trailing text the model may have added around the code block.
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in LLM response")
        report_data = json.loads(raw[start:end])
    except Exception as exc:
        logger.error("Report generation failed: %s — raw response: %r", exc, locals().get("raw", "<no response>"))
        report_data = {
            "summary_text": "Interview completed.",
            "strengths": ["Completed the interview"],
            "gaps": ["Report could not be generated automatically"],
        }

    return crud.create_report(
        db=db,
        session_id=session.id,
        summary_text=report_data.get("summary_text", ""),
        strengths=report_data.get("strengths", []),
        gaps=report_data.get("gaps", []),
        overall_score=overall,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_history(session: models.InterviewSession) -> list[dict]:
    history = []
    for q in session.questions:
        if q.answer:
            history.append(
                {
                    "question": q.question_text,
                    "answer": q.answer.answer_text,
                    "score": q.answer.eval_score or 0,
                    "topic": q.topic,
                    "difficulty": q.difficulty,
                }
            )
    return history


def _question_to_out(q: models.Question, total: int) -> QuestionOut:
    return QuestionOut(
        id=q.id,
        text=q.question_text,
        topic=q.topic,
        difficulty=q.difficulty,
        order_index=q.order_index,
        total_questions=total,
    )


def _generate_and_save_question(
    db: Session,
    session: models.InterviewSession,
    order_index: int,
) -> models.Question:
    resume = session.resume
    role = session.role
    history = _build_history(session)

    queries = context_builder.build_queries(
        profile_summary=resume.profile_summary or "",
        skills=resume.parsed_skills or [],
        technologies=resume.parsed_technologies or [],
        role_name=role.name,
        session_history=history,
    )
    chunks = rag_engine.retrieve(
        collection_name=role.kb_collection_name,
        queries=queries,
        top_k=settings.RETRIEVAL_TOP_K,
    )
    retrieval_query = context_builder.primary_query_string(queries)

    generated = question_generator.generate_question(
        role_name=role.name,
        profile_summary=resume.profile_summary or "",
        skills=resume.parsed_skills or [],
        technologies=resume.parsed_technologies or [],
        chunks=chunks,
        session_history=history,
        retrieval_query=retrieval_query,
    )

    return crud.create_question(
        db=db,
        session_id=session.id,
        order_index=order_index,
        question_text=generated.question,
        topic=generated.topic,
        difficulty=generated.difficulty,
        retrieval_query=retrieval_query,
        source_chunk_ids=generated.source_chunk_ids,
        rationale=generated.rationale,
    )


# ── Public interface ───────────────────────────────────────────────────────────

def start_interview(db: Session, resume_id: int, role_id: int) -> dict:
    """
    Create session, generate Q1, return {session, question_out}.
    """
    resume = crud.get_resume(db, resume_id)
    if not resume:
        raise ValueError(f"Resume {resume_id} not found.")
    role = crud.get_role(db, role_id)
    if not role:
        raise ValueError(f"Role {role_id} not found.")

    # Anonymous candidate per-session (no auth required)
    candidate = crud.create_candidate(db)
    session = crud.create_session(db, candidate.id, resume_id, role_id)

    # Generate first question
    question = _generate_and_save_question(db, session, order_index=1)

    # Transition to in_progress
    session.current_index = 1
    crud.update_session_status(db, session, "in_progress")

    total = settings.MAX_QUESTIONS_PER_INTERVIEW
    return {"session": session, "question_out": _question_to_out(question, total)}


def submit_answer(db: Session, session_id: int, answer_text: str) -> dict:
    """
    Evaluate current answer, advance state machine, return result dict.
    """
    session = crud.get_session(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found.")
    if session.status == "completed":
        raise ValueError("This interview session is already completed.")
    if session.status == "created":
        raise ValueError("Interview has not been started yet.")
    if not answer_text.strip():
        raise ValueError("Answer text cannot be empty.")

    current_q = crud.get_question_by_index(db, session_id, session.current_index)
    if not current_q:
        raise ValueError("Current question not found.")
    if current_q.answer:
        raise ValueError("This question has already been answered.")

    # Evaluate
    role = session.role
    eval_result = evaluator.evaluate_answer(
        question=current_q.question_text,
        answer=answer_text,
        topic=current_q.topic,
        role_name=role.name,
    )
    crud.create_answer(
        db=db,
        question_id=current_q.id,
        session_id=session_id,
        answer_text=answer_text,
        eval_score=eval_result.score,
        eval_feedback=eval_result.feedback,
    )

    total = settings.MAX_QUESTIONS_PER_INTERVIEW
    next_index = session.current_index + 1

    if session.current_index >= total:
        # Interview complete
        crud.update_session_status(db, session, "completed")
        # Refresh session to include newly saved answer for report generation
        db.refresh(session)
        _generate_report(db, session)
        return {
            "eval_score": eval_result.score,
            "eval_feedback": eval_result.feedback,
            "next_question": None,
            "status": "completed",
        }

    # Generate next question adaptively
    session.current_index = next_index
    db.commit()
    db.refresh(session)

    next_q = _generate_and_save_question(db, session, order_index=next_index)

    return {
        "eval_score": eval_result.score,
        "eval_feedback": eval_result.feedback,
        "next_question": _question_to_out(next_q, total),
        "status": "in_progress",
    }


def get_current_question(db: Session, session_id: int) -> dict:
    session = crud.get_session(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found.")

    total = settings.MAX_QUESTIONS_PER_INTERVIEW
    if session.status == "completed":
        return {"session": session, "question_out": None}

    q = crud.get_question_by_index(db, session_id, session.current_index)
    question_out = _question_to_out(q, total) if q else None
    return {"session": session, "question_out": question_out}


def regenerate_report(db: Session, session_id: int) -> models.Report:
    """Delete any existing report and regenerate it from the stored transcript."""
    session = crud.get_session(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found.")
    if session.status != "completed":
        raise ValueError("Cannot regenerate report for an incomplete session.")
    crud.delete_report(db, session_id)
    return _generate_report(db, session)
