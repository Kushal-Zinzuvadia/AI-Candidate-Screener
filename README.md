# AI Candidate Screener

An AI-powered technical interview system that uses RAG (Retrieval-Augmented Generation) to conduct adaptive, grounded technical interviews based on a candidate's resume.

## Quick Start

### Option A — Manual Setup (Recommended for local dev)

**Prerequisites:** Python 3.11+, Node.js 20+

**1. Backend setup**
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

**2. Configure environment**
```bash
cp .env.example .env
# Edit .env and set LLM_API_KEY to your Anthropic or OpenAI key
```

**3. Ingest knowledge bases** *(run once before starting the server)*
```bash
python ingestion/ingest.py --role ai_ml
python ingestion/ingest.py --role backend_engineering
```

**4. Start backend**
```bash
uvicorn app.main:app --reload
# API running at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

**5. Frontend setup**
```bash
cd ../frontend
npm install
npm run dev
# App running at http://localhost:3000
```

### Option B — Docker Compose

```bash
# 1. Set your API key in backend/.env
cp backend/.env.example backend/.env
# Edit backend/.env → set LLM_API_KEY

# 2. Start all services
docker compose up --build

# 3. Run ingestion (from inside the backend container)
docker compose exec backend python ingestion/ingest.py --role ai_ml
docker compose exec backend python ingestion/ingest.py --role backend_engineering
```

---

## Architecture

```
Frontend (Next.js)
      │ REST
      ▼
FastAPI Backend
  ├── Resume Parser (hybrid: taxonomy match + LLM)
  ├── Context Builder (builds 2-3 sub-queries per retrieval)
  ├── RAG Engine (ChromaDB, all-MiniLM-L6-v2 embeddings)
  ├── Question Generator (LLM + Pydantic validation + fallback)
  ├── Evaluator (LLM, scores 0-5)
  └── Session Manager (state machine: created → in_progress → completed)
      │
  ┌───┴───┐
  │       │
ChromaDB  SQLite/PostgreSQL
(vectors) (sessions, Q&A, reports)
```

For a detailed architecture diagram, see [`development_plan.md §3`](development_plan.md).

---

## Design Decisions

### Why Groq as the LLM provider?
Groq's free tier requires no credit card, allows ~1,000 requests/day at ~30 req/min, and its LPU hardware delivers sub-second response times — ideal for a live demo where latency is visible. A 6-question interview costs ~12–15 LLM calls total, comfortably within the daily cap for dev + demo use. `anthropic` and `openai` are still supported as fallbacks via `LLM_PROVIDER` in `.env`. The retry-with-backoff in `llm_client.py` handles transient 429s automatically.
SQLite requires zero setup for a 48h demo. The ORM (`SQLAlchemy`) is the only layer that touches the database; switching to PostgreSQL is a one-line change in `.env` (`DATABASE_URL=postgresql://...`). The Docker Compose file includes Postgres for anyone who wants it.

### Why ChromaDB over FAISS or Pinecone?
ChromaDB is persistent (survives restarts), Python-native, and requires no external service or signup. FAISS is faster for pure ANN search but is purely in-memory and requires manual serialization. Pinecone is excellent but requires API keys and an external dependency. For a demo environment, ChromaDB's tradeoffs are the right call.

### Why all-MiniLM-L6-v2?
384-dimensional, fast inference (~50ms/query on CPU), no API cost or rate limit risk, and good enough for topical retrieval. The abstraction in `rag_engine.py` means swapping to `text-embedding-3-small` or any other model is a one-line env change.

### Why hybrid resume parsing?
Pure LLM extraction hallucinated skill names in early testing. The deterministic taxonomy pass is reliable but misses synonyms (e.g., "sklearn" vs "scikit-learn"). The hybrid approach gets the best of both: deterministic correctness for known skills, LLM coverage for everything else. Trade-off: the taxonomy needs manual maintenance as new frameworks emerge.

### Why multi-query RAG?
A single query misses chunks that use different phrasing. The three-query strategy (skill-overlap, gap-coverage, follow-up) retrieves content from multiple semantic angles and merges/deduplicates results. This is documented in `context_builder.py` and surfaces meaningfully in the "why this was asked" traceability panel.

### Why SQLAlchemy create_all instead of Alembic?
For a 48h project with a stable schema, running migrations is unnecessary overhead. `Base.metadata.create_all()` is called at startup. This is explicitly noted as a known limitation.

---

## Known Limitations

- **No authentication**: interviews are anonymous. Anyone with a session ID can view results.
- **SQLite concurrency**: SQLite doesn't support concurrent writes. Under load, use PostgreSQL.
- **LLM costs**: each interview costs ~10-15 LLM API calls. No hard cost cap is implemented.
- **PDF only**: resume upload accepts PDF only. DOCX support would require `python-docx`.
- **Knowledge base**: uses curated in-repo text files. Higher quality would come from authoritative books/docs (e.g., *The Hundred-Page ML Book*).
- **No real-time updates**: the frontend polls on page transitions, not WebSockets.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/roles` | List roles with KB readiness |
| POST | `/api/resumes/upload` | Upload + parse resume |
| POST | `/api/interviews` | Start interview session |
| GET | `/api/interviews/{id}/current-question` | Re-fetch current question |
| POST | `/api/interviews/{id}/answer` | Submit answer, get next question |
| GET | `/api/interviews/{id}/summary` | Final report |

Full interactive docs: `http://localhost:8000/docs`

---

## What I Would Change With More Time

1. **Alembic migrations** — proper schema versioning instead of create_all.
2. **Streaming LLM responses** — stream question generation to the frontend for better perceived performance.
3. **Per-topic radar chart** — visualize skill coverage on the summary screen.
4. **Downloadable PDF report** — export results using `weasyprint` or similar.
5. **DOCX support** — `python-docx` for Word resume formats.
6. **Auth layer** — JWT-based sessions tied to email/OAuth.
7. **Better KB sources** — authoritative book chapters would improve retrieval quality significantly.