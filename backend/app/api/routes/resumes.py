import os
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.resume_parser import parse_resume
from app.db.crud import create_candidate, create_resume
from app.db.database import get_db
from app.db.schemas import ResumeParsedResponse

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf"}


@router.post("/upload", response_model=ResumeParsedResponse)
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Validate file type
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only PDF files are accepted.",
        )

    # Save file
    file_id = uuid.uuid4().hex
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

    try:
        parsed = parse_resume(file.file, file.filename or "resume.pdf")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {exc}")

    # Persist file
    with open(save_path, "wb") as f:
        file.file.seek(0)
        f.write(file.file.read())

    # Create anonymous candidate + resume records
    candidate = create_candidate(db)
    resume = create_resume(
        db=db,
        candidate_id=candidate.id,
        file_path=save_path,
        raw_text=parsed["raw_text"],
        parsed_skills=parsed["parsed_skills"],
        parsed_technologies=parsed["parsed_technologies"],
        profile_summary=parsed["profile_summary"],
    )

    return ResumeParsedResponse(
        resume_id=resume.id,
        candidate_id=candidate.id,
        parsed_skills=resume.parsed_skills,
        parsed_technologies=resume.parsed_technologies,
        profile_summary=resume.profile_summary,
    )
