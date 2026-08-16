"""
Hybrid resume parser (§7):
  1. Deterministic pass — keyword/regex match against a curated taxonomy.
  2. LLM pass — catch synonyms and derive a 2-3 sentence profile_summary.
  3. Merge + dedupe both lists.

Design decision: the hybrid approach gives reliability (taxonomy never
hallucinates) plus coverage (LLM catches "sklearn" → "scikit-learn" etc.).
Using only an LLM pass is fragile; using only the taxonomy misses phrasing.
"""
import json
import logging
import re
from pathlib import Path
from typing import IO

import fitz  # PyMuPDF

from app.core.llm_client import call_llm

logger = logging.getLogger(__name__)

# ── Taxonomy ──────────────────────────────────────────────────────────────────

SKILLS_TAXONOMY = [
    # Programming languages
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
    "Scala", "Kotlin", "Swift", "Ruby", "PHP", "R", "MATLAB",
    # ML / AI
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "Reinforcement Learning", "Transfer Learning", "Fine-tuning",
    "PyTorch", "TensorFlow", "Keras", "scikit-learn", "Hugging Face",
    "BERT", "GPT", "Transformers", "LangChain", "LlamaIndex", "RAG",
    # Data
    "Pandas", "NumPy", "Spark", "Hadoop", "Airflow", "dbt",
    # Backend
    "FastAPI", "Flask", "Django", "Spring Boot", "Express", "Node.js",
    "REST API", "GraphQL", "gRPC", "WebSockets",
    # Databases
    "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Cassandra",
    "Elasticsearch", "DynamoDB", "BigQuery", "Snowflake",
    # Cloud / DevOps
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform",
    "CI/CD", "GitHub Actions", "Jenkins",
    # General
    "SQL", "Linux", "Git", "Agile", "Microservices", "System Design",
]

_SKILLS_LOWER = {s.lower(): s for s in SKILLS_TAXONOMY}


def _deterministic_extract(text: str) -> tuple[list[str], list[str]]:
    """Return (skills, technologies) via case-insensitive keyword match."""
    text_lower = text.lower()
    matched = set()
    for kw_lower, kw_canonical in _SKILLS_LOWER.items():
        pattern = r"\b" + re.escape(kw_lower) + r"\b"
        if re.search(pattern, text_lower):
            matched.add(kw_canonical)

    # Split into "skills" (capabilities) vs "technologies" (tools/frameworks)
    tech_keywords = {
        "PyTorch", "TensorFlow", "Keras", "scikit-learn", "Hugging Face",
        "LangChain", "LlamaIndex", "FastAPI", "Flask", "Django", "Spring Boot",
        "Express", "Node.js", "Pandas", "NumPy", "Spark", "Hadoop", "Airflow",
        "dbt", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Cassandra",
        "Elasticsearch", "DynamoDB", "BigQuery", "Snowflake", "AWS", "GCP",
        "Azure", "Docker", "Kubernetes", "Terraform", "GitHub Actions", "Jenkins",
    }
    technologies = [m for m in matched if m in tech_keywords]
    skills = [m for m in matched if m not in tech_keywords]
    return skills, technologies


_LLM_SYSTEM = """You are a technical recruiter assistant. Given raw resume text, extract:
- skills: capabilities/concepts the candidate demonstrates (not tool names)
- technologies: specific tools, frameworks, libraries mentioned
- profile_summary: 2-3 sentence professional summary of the candidate

Only extract items actually present in the resume text. Do not invent anything.
Respond ONLY as valid JSON matching exactly:
{"skills": [string], "technologies": [string], "profile_summary": string}"""


def _llm_extract(raw_text: str) -> dict:
    truncated = raw_text[:4000]  # stay within context limits
    user = f"Resume text:\n\n{truncated}"
    try:
        response = call_llm(_LLM_SYSTEM, user, max_tokens=600)
        # Strip markdown code fences if present
        response = re.sub(r"^```(?:json)?\s*", "", response.strip())
        response = re.sub(r"\s*```$", "", response.strip())
        return json.loads(response)
    except Exception as exc:
        logger.warning("LLM extraction failed: %s", exc)
        return {"skills": [], "technologies": [], "profile_summary": ""}


def extract_text_from_pdf(file_obj: IO[bytes]) -> str:
    """Extract raw text from a PDF file object using PyMuPDF."""
    data = file_obj.read()
    doc = fitz.open(stream=data, filetype="pdf")
    pages = [page.get_text() for page in doc]
    return "\n\n".join(pages)


def parse_resume(file_obj: IO[bytes], filename: str) -> dict:
    """
    Full hybrid parse. Returns:
      {raw_text, parsed_skills, parsed_technologies, profile_summary}
    """
    raw_text = extract_text_from_pdf(file_obj)
    if not raw_text.strip():
        raise ValueError("Could not extract text from the uploaded file.")

    det_skills, det_tech = _deterministic_extract(raw_text)
    llm_result = _llm_extract(raw_text)

    # Merge + dedupe (case-insensitive)
    def merge(a: list, b: list) -> list:
        seen = {x.lower() for x in a}
        merged = list(a)
        for item in b:
            if item.lower() not in seen:
                seen.add(item.lower())
                merged.append(item)
        return merged

    return {
        "raw_text": raw_text,
        "parsed_skills": merge(det_skills, llm_result.get("skills", [])),
        "parsed_technologies": merge(det_tech, llm_result.get("technologies", [])),
        "profile_summary": llm_result.get("profile_summary", "").strip()
        or "Resume uploaded — no summary extracted.",
    }
