import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import engine, SessionLocal
from app.db import models
from app.db.crud import seed_roles
from app.api.routes import roles, resumes, interviews, reports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Candidate Screener",
    description="RAG-powered technical interview system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roles.router)
app.include_router(resumes.router)
app.include_router(interviews.router)
app.include_router(reports.router)


@app.on_event("startup")
def startup():
    logger.info("Creating database tables...")
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_roles(db)
        logger.info("Roles seeded.")
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
