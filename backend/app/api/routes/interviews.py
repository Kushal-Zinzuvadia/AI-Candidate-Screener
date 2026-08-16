from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import session_manager
from app.db.database import get_db
from app.db.schemas import (
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    CurrentQuestionResponse,
    InterviewStartRequest,
    InterviewStartResponse,
)

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


@router.post("", response_model=InterviewStartResponse)
def start_interview(payload: InterviewStartRequest, db: Session = Depends(get_db)):
    try:
        result = session_manager.start_interview(db, payload.resume_id, payload.role_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {exc}")

    return InterviewStartResponse(
        session_id=result["session"].id,
        status=result["session"].status,
        question=result["question_out"],
    )


@router.get("/{session_id}/current-question", response_model=CurrentQuestionResponse)
def get_current_question(session_id: int, db: Session = Depends(get_db)):
    try:
        result = session_manager.get_current_question(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return CurrentQuestionResponse(
        session_id=session_id,
        status=result["session"].status,
        question=result["question_out"],
    )


@router.post("/{session_id}/answer", response_model=AnswerSubmitResponse)
def submit_answer(
    session_id: int,
    payload: AnswerSubmitRequest,
    db: Session = Depends(get_db),
):
    if not payload.answer_text.strip():
        raise HTTPException(status_code=400, detail="Answer text cannot be empty.")

    try:
        result = session_manager.submit_answer(db, session_id, payload.answer_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {exc}")

    return AnswerSubmitResponse(
        eval_score=result["eval_score"],
        eval_feedback=result["eval_feedback"],
        next_question=result["next_question"],
        status=result["status"],
    )


@router.post("/{session_id}/regenerate-report")
def regenerate_report(session_id: int, db: Session = Depends(get_db)):
    try:
        session_manager.regenerate_report(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate report: {exc}")
    
    return {"status": "success"}
