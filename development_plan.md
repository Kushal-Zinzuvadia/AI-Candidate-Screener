# Candidate Screening System — AI-Driven Development Plan

**Assignment:** AI/ML & Backend Engineering Intern — PG-AGI
**Window:** 48 hours from receipt
**Purpose of this document:** a build spec detailed enough to hand to an AI coding assistant (Claude Code, Cursor, etc.) one section at a time, or to follow yourself as a checklist.

---

## 0. How to Use This Plan

- Sections 6–12 are self-contained module specs — feed each one to your AI assistant in order and it can scaffold that module directly.
- Section 15 is the actual hour-by-hour schedule. Section 16 gives copy-pasteable prompts for each phase.
- Section 14 tells you what to cut first if you're running out of time — **read this before you start**, so every decision you make is already ranked by priority.
- Defaults (chunk sizes, k-values, model names) are starting points, not requirements. State your reasoning for any change in the README — the rubric explicitly rewards that.

---

## 1. What's Actually Being Graded

| Rubric item (from the brief) | Where this plan addresses it |
|---|---|
| RAG pipeline: ingestion, chunking, embeddings, retrieval | §6 |
| Resume meaningfully influences topic/difficulty/direction | §7, §8 |
| Modular backend, separation of concerns, env-based config | §3, §4, §13 |
| Session continuity, optional adaptive questioning | §9 |
| Structured storage + traceability of question generation | §5, §8.3 |
| Frontend state handling across interview stages | §11 |
| "Clarity of thought" / design-decision reasoning | §18 (README template) |

Keep this table in mind — a working demo with weak reasoning scores lower than a smaller demo with sharp, explained trade-offs.

---

## 2. Recommended Tech Stack

| Layer | Choice | Why | Alternative if blocked |
|---|---|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind | Fast to scaffold, SSR not actually needed but file-based routing keeps 3 screens organized | Plain React + Vite if Next.js feels heavy |
| Backend | FastAPI (Python 3.11+) | Async, automatic OpenAPI docs (useful for the demo video), Pydantic validation for free | Flask + Pydantic manually |
| Relational DB | PostgreSQL via Docker | Shows production intent; JSON columns for flexible fields | SQLite (fine for 48h, note the trade-off in README) |
| ORM | SQLAlchemy 2.0 + Alembic | Swapping Postgres↔SQLite becomes a one-line change | — |
| Vector store | ChromaDB (local, persistent) | Zero external signup, Python-native, per-role collections | FAISS if you want raw speed and don't need metadata filtering |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local, free) | No API cost/rate limit risk during a 48h clock | OpenAI `text-embedding-3-small` if you have budget and want higher quality |
| LLM (question gen + evaluation) | **Groq API** (Llama 3.3 70B or Llama 3.1 8B) | Free tier, no credit card: ~30 requests/min, ~1,000 requests/day, 6–12K tokens/min depending on model. Sign up in ~2 min at console.groq.com. LPU hardware means sub-second responses — good for a live demo | Google AI Studio / Gemini free tier (1,500 req/day, higher token volume, slightly slower) as a second free option or backup key |
| Resume text extraction | PyMuPDF (`fitz`) | Fast, handles most resume PDFs cleanly | `pdfplumber` if layout is unusual |
| Containerization | Docker Compose | One command spins up backend + frontend + db — makes the demo video trivial | Skip if truly short on time; document manual setup instead |
| Frontend state | React Context or Zustand | Interview flow only needs a handful of shared values — don't reach for Redux | — |

---

## 3. High-Level Architecture

```
┌──────────────┐        ┌───────────────────────────────────────────────┐
│   Frontend    │◄──────►│                  FastAPI Backend               │
│  (Next.js)    │  REST  │                                                 │
└──────────────┘        │  ┌───────────────┐   ┌────────────────────┐    │
                         │  │ Resume Parser  │   │ Session Manager     │    │
                         │  └───────┬───────┘   └────────┬───────────┘    │
                         │          │                    │                │
                         │  ┌───────▼───────┐   ┌────────▼───────────┐    │
                         │  │Context Builder │──►│ Question Generator  │    │
                         │  └───────┬───────┘   └────────┬───────────┘    │
                         │          │                    │                │
                         │  ┌───────▼───────┐            │                │
                         │  │  RAG Engine    │            │                │
                         │  │ (retrieval)    │            ▼                │
                         │  └───────┬───────┘   ┌────────────────────┐    │
                         │          │           │     Evaluator       │    │
                         │          │           └────────┬───────────┘    │
                         └──────────┼────────────────────┼────────────────┘
                                    │                     │
                          ┌─────────▼─────────┐  ┌────────▼─────────┐
                          │  ChromaDB (vectors) │  │ PostgreSQL (state) │
                          │  per-role collection │  │ sessions/Q/A/report│
                          └────────────────────┘  └───────────────────┘
```

Offline/one-time process (run before demo, not per-request): **Knowledge Ingestion** — loads role PDFs → chunks → embeds → writes to ChromaDB. This never touches the request path.

---

## 4. Repository Structure

```
candidate-screening-system/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py                  # pydantic-settings, reads .env
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── resumes.py
│   │   │       ├── roles.py
│   │   │       ├── interviews.py
│   │   │       └── reports.py
│   │   ├── core/
│   │   │   ├── resume_parser.py
│   │   │   ├── context_builder.py
│   │   │   ├── rag_engine.py
│   │   │   ├── question_generator.py
│   │   │   ├── evaluator.py
│   │   │   └── session_manager.py
│   │   └── db/
│   │       ├── models.py
│   │       ├── schemas.py             # Pydantic request/response models
│   │       ├── database.py
│   │       └── crud.py
│   ├── ingestion/
│   │   ├── ingest.py                  # CLI: python ingest.py --role ai_ml
│   │   ├── chunker.py
│   │   └── kb_sources/
│   │       ├── ai_ml/                 # source PDFs/text for that role
│   │       └── backend_engineering/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx                       # upload + role select
│   │   ├── interview/[sessionId]/page.tsx
│   │   └── interview/[sessionId]/summary/page.tsx
│   ├── components/
│   ├── lib/api.ts
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── README.md
└── docs/
    └── architecture.md                # can just be this plan, trimmed
```

---

## 5. Database Schema

| Table | Key columns | Notes |
|---|---|---|
| `candidates` | id, name, email (optional), created_at | Can be a throwaway/anonymous record if you skip auth |
| `resumes` | id, candidate_id, file_path, raw_text, parsed_skills (JSON), parsed_technologies (JSON), profile_summary (text), uploaded_at | `profile_summary` = short LLM/rule-based synopsis used for query building |
| `roles` | id, name, description, kb_collection_name | Seeded at ingestion time, not user-created |
| `interview_sessions` | id, candidate_id, resume_id, role_id, status (`created`/`in_progress`/`completed`), current_index, created_at, completed_at | Status drives the state machine (§9) |
| `questions` | id, session_id, order_index, question_text, topic, difficulty, retrieval_query (text), source_chunk_ids (JSON), created_at | `source_chunk_ids` is your traceability requirement (§7.5 of brief) |
| `answers` | id, question_id, session_id, answer_text, submitted_at, eval_score (0–5), eval_feedback (text) | One-to-one with questions |
| `reports` | id, session_id, summary_text, strengths (JSON), gaps (JSON), overall_score, generated_at | Built once at session completion |

Use SQLAlchemy models mirroring this directly; Alembic for migrations if time allows, otherwise `Base.metadata.create_all()` on startup is fine for a 48h project — say so in the README rather than pretending it's production-grade.

---

## 6. RAG Pipeline Design

### 6.1 Knowledge Base Sourcing
- **AI/ML Engineer role:** use *The Hundred-Page Machine Learning Book* as the primary corpus — it's compact and well-structured by topic, which makes chunking and topic-tagging easier than Mitchell's or Bishop's denser texts. Add chapters from Mitchell's book for a "hard mode" if time allows.
- **Data Science role:** *Introduction to Machine Learning with Python*.
- **Backend Engineer role** (no book supplied, but the brief's example flow names this role explicitly): source an openly-licensed corpus rather than scraping proprietary text — e.g. the MIT-licensed **system-design-primer** GitHub repo, or official FastAPI/PostgreSQL documentation. Document this sourcing choice in the README; it's a legitimate design decision, not a shortcut.
- Implement at least **two roles end-to-end** rather than stretching thin across many — depth over breadth scores better against "conceptual and applied understanding."

### 6.2 Ingestion & Chunking
- Extract text with PyMuPDF, preserving chapter/section headers as metadata.
- Chunk with a recursive splitter: **~500 tokens, ~75-token overlap**. Prefer splitting on section boundaries over hard token cuts where headers are detectable — this preserves context better than naive fixed-width splitting.
- Metadata per chunk: `role`, `source_title`, `section`, `page_number`, `chunk_id`. This metadata is what makes traceability possible later.
- Store one **Chroma collection per role** (`kb_ai_ml`, `kb_backend_engineering`) — keeps retrieval scoped and avoids cross-role contamination.
- Run ingestion as an offline CLI (`python ingestion/ingest.py --role ai_ml --source kb_sources/ai_ml/`), not inside the request path.

### 6.3 Embeddings
- Local `all-MiniLM-L6-v2` by default — 384-dim, fast, no external dependency, good enough for topical retrieval (you're not doing legal-grade semantic search).
- If you swap to an API embedding model, keep the interface abstracted (`embed(text: str) -> list[float]`) so the choice is a one-line swap — worth mentioning as a design decision.

### 6.4 Query Construction & Retrieval
Don't retrieve on a single flat query — generate **2–4 sub-queries** covering different angles, then merge:
1. *Skill-overlap query* — built from resume skills that match the role's domain (goes deeper on what the candidate claims to know).
2. *Gap-coverage query* — role-fundamental topics **not** evident in the resume (tests foundational breadth).
3. *Follow-up query* (adaptive, from question 2 onward) — built from the topic of the previous answer, especially if it scored low.

For each sub-query: retrieve top-k (k=4) from the role's Chroma collection, merge results, de-duplicate by `chunk_id`, cap total context to a token budget (~1500 tokens) before passing to the question generator. This multi-query approach is worth calling out explicitly in your README as it directly answers the brief's "ensure retrieved content is actually useful" requirement.

---

## 7. Resume Parsing Design

Use a **hybrid** approach rather than pure LLM extraction (more reliable, and shows engineering judgment):

1. Extract raw text (PyMuPDF).
2. **Deterministic pass:** match against a small curated skills/technologies taxonomy (a plain list — Python, FastAPI, React, Docker, SQL, PyTorch, etc.) using simple keyword/regex matching. Fast, reliable, zero hallucination risk.
3. **LLM pass:** send the raw text with instructions to extract skills/technologies/domain exposure *only if present in the text*, plus a 2–3 sentence `profile_summary`. This catches synonyms and phrasing the taxonomy misses.
4. Merge both lists (dedupe), store `parsed_skills`, `parsed_technologies`, `profile_summary` on the `resumes` row.

This combination — not just an LLM call — is a good thing to highlight in the README under "design decisions," since it directly targets the reliability concern an evaluator will have about LLM-only extraction.

---

## 8. Question Generation Design

### 8.1 Prompt Template (starting point)

```
SYSTEM:
You are conducting a technical interview for the role of {role_name}.
Ask exactly one question, grounded ONLY in the provided context chunks.
Do not introduce facts, terms, or examples that are not supported by the
context or the candidate's resume. Calibrate depth to the candidate's
apparent experience level and to their performance so far in this session.

USER:
Role: {role_name}
Candidate profile summary: {profile_summary}
Candidate skills: {skill_list}

Retrieved context (use only this for factual grounding):
[C1] ({source_title}, {section}): {chunk_text}
[C2] ({source_title}, {section}): {chunk_text}
...

Interview history so far:
Q1: {question_1} | A1: {answer_1} | Score: {score_1}
...

Instructions:
- If the previous answer scored 4-5, go deeper on the same topic or raise difficulty.
- If it scored 1-2, pivot to a different foundational topic from the context, at a simpler level.
- Reference which context chunk(s) informed this question.

Respond ONLY as JSON matching this schema:
{
  "question": string,
  "topic": string,
  "difficulty": "easy" | "medium" | "hard",
  "source_chunk_ids": [string],
  "rationale": string   // 1 sentence, internal use, not shown to candidate
}
```

### 8.2 Structured Output
Validate the LLM's JSON against a Pydantic model before saving — if it fails, retry once with a stricter reminder, then fall back to a template question tagged `topic="general"` so the interview never hard-fails. Log failures; mention the fallback in your README as intentional robustness, not a bug.

### 8.3 Traceability
Every `questions` row stores the `retrieval_query` used and `source_chunk_ids`. Surface this on the summary screen (§12) as a small "why this was asked" expandable — directly satisfies the brief's explicit traceability requirement and is a cheap, visible way to score well on "system design maturity."

---

## 9. Adaptive Interview State Machine

```
CREATED ──(first question generated)──► IN_PROGRESS ──(answer N submitted, N == max)──► COMPLETED
                                              │
                                              └──(answer < max)── loop: evaluate → build next query → generate next question
```

| Previous answer score | Next-question behavior |
|---|---|
| 4–5 (strong) | Same topic, increase difficulty, or move to an adjacent advanced topic |
| 3 (adequate) | Different topic at similar difficulty (breadth) |
| 1–2 (weak) | Simpler question, same or foundational topic (don't just move on — check understanding) |

Fix `max_questions` via env var (default 6) rather than hardcoding — keeps a demo run short and predictable. Session `status` transitions are the only source of truth for what the frontend should render next; don't duplicate that logic client-side.

---

## 10. API Design

| Method | Endpoint | Purpose | Key request fields | Key response fields |
|---|---|---|---|---|
| GET | `/api/roles` | List roles + KB readiness | — | `[{id, name, description}]` |
| POST | `/api/resumes/upload` | Upload + parse resume | multipart file | `{resume_id, parsed_skills, parsed_technologies, profile_summary}` |
| POST | `/api/interviews` | Start session, generate Q1 | `{resume_id, role_id}` | `{session_id, question}` |
| GET | `/api/interviews/{id}/current-question` | Re-fetch current question (page refresh safety) | — | `{question, order_index, status}` |
| POST | `/api/interviews/{id}/answer` | Submit answer, get next question or completion | `{answer_text}` | `{eval_score, eval_feedback, next_question \| status: "completed"}` |
| GET | `/api/interviews/{id}/summary` | Final structured report | — | `{overall_score, strengths, gaps, transcript[]}` |

Validation/error handling to actually implement (don't skip — it's explicitly called out in the brief): missing/empty file upload, unsupported role_id, answer submitted after session already completed, LLM/JSON-parse failure (falls back per §8.2), empty answer text.

---

## 11. Frontend Design

Three screens, matching the state machine:

1. **`/` — Entry:** resume upload (drag/drop or file picker) + role dropdown (populated from `/api/roles`) → "Start Interview" calls `POST /api/interviews`, routes to `/interview/{sessionId}`.
2. **`/interview/[sessionId]` — Interview:** shows current question, a progress indicator (`Question 3 of 6`), textarea + submit. On submit, show brief eval feedback (optional but nice), then transition to next question or redirect to summary when `status: "completed"`.
3. **`/interview/[sessionId]/summary` — Results:** overall score, per-question breakdown (question, answer, score, and a collapsible "why this was asked" showing topic + source chunk snippet), strengths/gaps lists.

State to actually track client-side: `sessionId`, current question object, loading/submitting flags. Everything else (history, scores) should be re-fetchable from the backend, not held only in client memory — protects against refresh/navigation losing state, and demonstrates "session continuity" cleanly in the demo video.

---

## 12. Final Report Design

`reports` generation (triggered once, when session hits `completed`):
- Aggregate `eval_score` across all answers → `overall_score`.
- One LLM call summarizing the transcript into `strengths` (2–3 items) and `gaps` (2–3 items) — feed it the full Q&A history + scores, ask for JSON output, same validation pattern as §8.2.
- Store the report row; summary endpoint just reads it back (don't regenerate on every page load).

---

## 13. Environment & Configuration

```
DATABASE_URL=postgresql://user:pass@db:5432/screening
CHROMA_PERSIST_DIR=./chroma_data
LLM_PROVIDER=groq
GROQ_API_KEY=
LLM_MODEL=llama-3.3-70b-versatile   # or llama-3.1-8b-instant for higher throughput
EMBEDDING_MODEL=all-MiniLM-L6-v2
MAX_QUESTIONS_PER_INTERVIEW=6
RETRIEVAL_TOP_K=4
CORS_ORIGINS=http://localhost:3000
```

All of the above read via `pydantic-settings` in `config.py` — nothing hardcoded in business logic. This is explicitly named in the brief ("Configuration should be handled through environment variables") so it's an easy, visible point to nail.

---

## 14. MVP Priority Tiers

If the clock runs out, cut in this order — never cut P0.

**P0 — must work end-to-end for the demo:**
Resume upload → role select → question generated from real retrieved context → answer submission → 6-question loop → summary screen with scores. One role fully ingested and working.

**P1 — clearly strengthens the submission, do if time allows:**
Second role's knowledge base, adaptive difficulty logic (§9 table), traceability display on summary screen, Docker Compose one-command startup.

**P2 — stretch/creativity, only after P0+P1 are solid:**
Per-topic radar chart on summary, downloadable PDF report, candidate-facing hint system, resume-vs-role match score, multiple resume format support (DOCX).

---

## 15. 48-Hour Execution Timeline

The brief gives 48 wall-clock hours, not 48 work hours — plan around realistic focused blocks, not a nonstop sprint.

| Block | Focus | Deliverable at end of block |
|---|---|---|
| Day 1, Block 1 (~3h) | Repo skeleton, Docker Compose, DB models, `.env` setup | `docker compose up` boots empty backend + frontend + Postgres |
| Day 1, Block 2 (~4h) | Ingestion pipeline: chunker, embeddings, Chroma write for one role | CLI run populates `kb_ai_ml` collection; spot-check retrieval manually |
| Day 1, Block 3 (~4h) | Resume upload endpoint + hybrid parser (§7) | Upload a real PDF, get back structured skills/summary |
| Day 2, Block 1 (~4h) | Context builder + retrieval (§6.4) + question generator (§8) | `POST /api/interviews` returns a real, grounded first question |
| Day 2, Block 2 (~4h) | Answer endpoint, evaluator, adaptive loop, session state machine | Full 6-question loop completes via curl/Postman, no frontend yet |
| Day 2, Block 3 (~4h) | Frontend: three screens wired to the API | Full flow works clicking through the browser |
| Final Block (~3h) | Report generation, traceability UI, error handling pass, README, record demo video | Submission-ready |

That's ~26 focused hours inside the 48-hour window — leaves slack for debugging and rest.

---

## 16. Working With an AI Coding Assistant

Feed each module as its own prompt, referencing this plan's section numbers so the assistant has the contract, not just a vague ask.

**Ingestion:**
> "Using the design in §6 of the attached plan, write `ingestion/chunker.py` and `ingestion/ingest.py`. Recursive chunking at ~500 tokens/75 overlap, metadata per chunk as specified, write to a Chroma collection named `kb_{role}`."

**Resume parser:**
> "Implement `core/resume_parser.py` per §7 — deterministic taxonomy match plus one LLM call for extraction and profile_summary, merged and deduped. Taxonomy list: [supply your list]."

**Question generator:**
> "Implement `core/question_generator.py` using the prompt template in §8.1. Validate output against the Pydantic schema in §8.2; on failure retry once then fall back to a template question."

**Session/API layer:**
> "Implement the `/api/interviews` routes per the table in §10 and the state machine in §9, wired to the SQLAlchemy models in §5."

**Frontend:**
> "Build the three Next.js screens in §11, calling the endpoints in §10. Track sessionId and current question client-side; re-fetch history from the backend rather than holding it only in memory."

After each generated module, actually run it against a real input before moving to the next prompt — don't chain five modules unverified, since a wrong assumption in the ingestion step (e.g., chunk metadata shape) silently breaks question generation two steps later.

---

## 17. Testing & Validation Checklist

- [ ] Ingestion produces >0 chunks with correct metadata for each role
- [ ] Manual retrieval query returns topically relevant chunks (eyeball 3–5 results)
- [ ] Resume upload handles a real PDF and a malformed/empty file gracefully
- [ ] Question generator output validates against schema on 10+ consecutive calls
- [ ] Full interview loop (start → 6 answers → summary) completes without manual DB edits
- [ ] Refreshing `/interview/{sessionId}` mid-interview doesn't lose state
- [ ] Submitting an answer twice for the same question is rejected or handled explicitly
- [ ] `docker compose up` works from a clean clone (test this — it's the first thing an evaluator will try)

---

## 18. README & Demo Video Checklist

**README must include** (per the brief, this is graded, not optional):
- Setup instructions (ideally: `docker compose up` and nothing else)
- Architecture summary (can lift from §3)
- Explicit "Design Decisions" section covering: why this vector store, why this chunk size, why hybrid resume parsing, what you'd change with more time
- Known limitations (be upfront — this reads as maturity, not weakness)

**Demo video (mandatory) should show, in order:**
1. Uploading a resume and selecting a role
2. A generated question, with a moment showing it's grounded in retrieved context (e.g., open the "why this was asked" panel)
3. Answering 2–3 questions, including one adaptive difficulty change if implemented
4. The final summary screen with traceability visible
5. A 30-second narrated walkthrough of the backend architecture (terminal/code, not just UI)

---

## 19. Risk Mitigation

| Risk | Mitigation |
|---|---|
| Groq free-tier rate limit hit (30 req/min, ~1,000/day) mid-build or mid-demo | Add basic retry-with-backoff around LLM calls; during dev, avoid looping test scripts that fire many calls back-to-back. A 6-question interview is ~12–15 calls total (question gen + eval + final report) — well under the daily cap for normal dev + demo use |
| Groq deprecates/renames a preview model mid-build | Pin the model name in `.env`, not hardcoded in code, so swapping is a one-line change; `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` are both stable production model IDs, not previews |
| Local embedding model slow on CPU | You have a 4GB GPU — `sentence-transformers` will use it automatically if `torch` is installed with CUDA support; confirm with `torch.cuda.is_available()`. Not required (MiniLM is fast even on CPU) but free speedup if available |
| Question generator returns malformed JSON | Schema validation + single retry + template fallback (§8.2) — never let it 500 the request |
| Running out of time before frontend | Backend is independently demoable via `/docs` (FastAPI auto Swagger UI) and curl — still a valid partial demo |
| Docker Compose flaky on evaluator's machine | Document manual (non-Docker) setup steps as a fallback in the README |
| Only one role's KB actually solid | Say so explicitly rather than presenting a half-working second role as complete — honesty here scores better than overreach |

---

*End of plan. Sections 6–12 are written to be handed to an AI coding assistant module-by-module; verify each module's real output before moving to the next.*
