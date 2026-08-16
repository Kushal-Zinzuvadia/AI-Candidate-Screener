from datetime import datetime
from sqlalchemy.orm import Session
from app.db import models


# ── Candidate ─────────────────────────────────────────────────────────────────

def create_candidate(db: Session, name: str | None = None, email: str | None = None):
    candidate = models.Candidate(name=name, email=email)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


# ── Resume ────────────────────────────────────────────────────────────────────

def create_resume(
    db: Session,
    candidate_id: int,
    file_path: str,
    raw_text: str,
    parsed_skills: list,
    parsed_technologies: list,
    profile_summary: str,
):
    resume = models.Resume(
        candidate_id=candidate_id,
        file_path=file_path,
        raw_text=raw_text,
        parsed_skills=parsed_skills,
        parsed_technologies=parsed_technologies,
        profile_summary=profile_summary,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def get_resume(db: Session, resume_id: int):
    return db.query(models.Resume).filter(models.Resume.id == resume_id).first()


# ── Role ──────────────────────────────────────────────────────────────────────

def get_all_roles(db: Session):
    return db.query(models.Role).all()


def get_role(db: Session, role_id: int):
    return db.query(models.Role).filter(models.Role.id == role_id).first()


def seed_roles(db: Session):
    """Insert default roles if the table is empty."""
    if db.query(models.Role).first():
        return
    defaults = [
        models.Role(
            name="AI/ML Engineer",
            description="Covers machine learning, deep learning, NLP, and model evaluation.",
            kb_collection_name="kb_ai_ml",
        ),
        models.Role(
            name="Data Science / Applied ML",
            description="Covers applied machine learning, data preprocessing, model selection, and algorithm implementation.",
            kb_collection_name="kb_data_science",
        ),
    ]
    db.add_all(defaults)
    db.commit()


# ── InterviewSession ──────────────────────────────────────────────────────────

def create_session(db: Session, candidate_id: int, resume_id: int, role_id: int):
    session = models.InterviewSession(
        candidate_id=candidate_id,
        resume_id=resume_id,
        role_id=role_id,
        status="created",
        current_index=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int):
    return (
        db.query(models.InterviewSession)
        .filter(models.InterviewSession.id == session_id)
        .first()
    )


def update_session_status(db: Session, session: models.InterviewSession, status: str):
    session.status = status
    if status == "completed":
        session.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


def increment_session_index(db: Session, session: models.InterviewSession):
    session.current_index += 1
    db.commit()
    db.refresh(session)
    return session


# ── Question ──────────────────────────────────────────────────────────────────

def create_question(
    db: Session,
    session_id: int,
    order_index: int,
    question_text: str,
    topic: str,
    difficulty: str,
    retrieval_query: str,
    source_chunk_ids: list,
    rationale: str | None = None,
):
    question = models.Question(
        session_id=session_id,
        order_index=order_index,
        question_text=question_text,
        topic=topic,
        difficulty=difficulty,
        retrieval_query=retrieval_query,
        source_chunk_ids=source_chunk_ids,
        rationale=rationale,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_question_by_index(db: Session, session_id: int, order_index: int):
    return (
        db.query(models.Question)
        .filter(
            models.Question.session_id == session_id,
            models.Question.order_index == order_index,
        )
        .first()
    )


# ── Answer ────────────────────────────────────────────────────────────────────

def create_answer(
    db: Session,
    question_id: int,
    session_id: int,
    answer_text: str,
    eval_score: int,
    eval_feedback: str,
):
    answer = models.Answer(
        question_id=question_id,
        session_id=session_id,
        answer_text=answer_text,
        eval_score=eval_score,
        eval_feedback=eval_feedback,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


# ── Report ────────────────────────────────────────────────────────────────────

def create_report(
    db: Session,
    session_id: int,
    summary_text: str,
    strengths: list,
    gaps: list,
    overall_score: float,
):
    report = models.Report(
        session_id=session_id,
        summary_text=summary_text,
        strengths=strengths,
        gaps=gaps,
        overall_score=overall_score,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report(db: Session, session_id: int):
    return (
        db.query(models.Report)
        .filter(models.Report.session_id == session_id)
        .first()
    )


def delete_report(db: Session, session_id: int) -> None:
    db.query(models.Report).filter(models.Report.session_id == session_id).delete()
    db.commit()
