from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("Resume", back_populates="candidate")
    sessions = relationship("InterviewSession", back_populates="candidate")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    file_path = Column(String)
    raw_text = Column(Text)
    parsed_skills = Column(JSON, default=list)
    parsed_technologies = Column(JSON, default=list)
    profile_summary = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="resumes")
    sessions = relationship("InterviewSession", back_populates="resume")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(Text)
    kb_collection_name = Column(String)

    sessions = relationship("InterviewSession", back_populates="role")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    status = Column(String, default="created")  # created | in_progress | completed
    current_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    candidate = relationship("Candidate", back_populates="sessions")
    resume = relationship("Resume", back_populates="sessions")
    role = relationship("Role", back_populates="sessions")
    questions = relationship(
        "Question", back_populates="session", order_by="Question.order_index"
    )
    answers = relationship("Answer", back_populates="session")
    report = relationship("Report", back_populates="session", uselist=False)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"))
    order_index = Column(Integer)
    question_text = Column(Text)
    topic = Column(String)
    difficulty = Column(String)  # easy | medium | hard
    retrieval_query = Column(Text, nullable=True)
    source_chunk_ids = Column(JSON, default=list)
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False)


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    session_id = Column(Integer, ForeignKey("interview_sessions.id"))
    answer_text = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    eval_score = Column(Integer, nullable=True)  # 0–5
    eval_feedback = Column(Text, nullable=True)

    question = relationship("Question", back_populates="answer")
    session = relationship("InterviewSession", back_populates="answers")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), unique=True)
    summary_text = Column(Text)
    strengths = Column(JSON, default=list)
    gaps = Column(JSON, default=list)
    overall_score = Column(Float)
    generated_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="report")
