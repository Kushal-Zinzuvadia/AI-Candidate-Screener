from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import session_manager
from app.db.crud import get_report, get_session
from app.db.database import get_db
from app.db.schemas import SummaryResponse, TranscriptItem

router = APIRouter(prefix="/api/interviews", tags=["reports"])


@router.get("/{session_id}/summary", response_model=SummaryResponse)
def get_summary(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Interview is not completed yet. Complete all questions first.",
        )

    report = get_report(db, session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    transcript = []
    for q in session.questions:
        ans = q.answer
        transcript.append(
            TranscriptItem(
                order_index=q.order_index,
                question=q.question_text,
                topic=q.topic,
                difficulty=q.difficulty,
                answer=ans.answer_text if ans else "",
                score=ans.eval_score if ans else 0,
                feedback=ans.eval_feedback if ans else "",
                source_chunk_ids=q.source_chunk_ids or [],
                rationale=q.rationale,
            )
        )

    return SummaryResponse(
        session_id=session_id,
        overall_score=report.overall_score,
        strengths=report.strengths,
        gaps=report.gaps,
        summary_text=report.summary_text,
        transcript=transcript,
    )


@router.post("/{session_id}/regenerate-report", response_model=SummaryResponse)
def regenerate_report(session_id: int, db: Session = Depends(get_db)):
    try:
        report = session_manager.regenerate_report(db, session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    session = get_session(db, session_id)
    transcript = []
    for q in session.questions:
        ans = q.answer
        transcript.append(
            TranscriptItem(
                order_index=q.order_index,
                question=q.question_text,
                topic=q.topic,
                difficulty=q.difficulty,
                answer=ans.answer_text if ans else "",
                score=ans.eval_score if ans else 0,
                feedback=ans.eval_feedback if ans else "",
                source_chunk_ids=q.source_chunk_ids or [],
                rationale=q.rationale,
            )
        )

    return SummaryResponse(
        session_id=session_id,
        overall_score=report.overall_score,
        strengths=report.strengths,
        gaps=report.gaps,
        summary_text=report.summary_text,
        transcript=transcript,
    )
