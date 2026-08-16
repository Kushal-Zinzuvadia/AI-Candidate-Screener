"""
RAG engine (§6.4): multi-query retrieval with de-duplication and token budgeting.

Design decision: we generate 2-4 sub-queries covering different angles rather
than a single flat query. This increases recall for topics the candidate may
phrase differently and surfaces both skill-depth and gap-coverage chunks.
"""
import logging
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)

from typing import Any

# ── Singletons ────────────────────────────────────────────────────────────────

_chroma_client: Any | None = None
_embedding_model: SentenceTransformer | None = None


def _get_chroma() -> Any:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _chroma_client


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedding_model


def embed(text: str) -> list[float]:
    """Embed a single string. Interface: embed(text) -> list[float]."""
    model = _get_embedding_model()
    return model.encode(text).tolist()


# ── Collection helpers ────────────────────────────────────────────────────────

def collection_exists(collection_name: str) -> bool:
    try:
        client = _get_chroma()
        col = client.get_collection(collection_name)
        return col.count() > 0
    except Exception:
        return False


def get_collection(collection_name: str):
    return _get_chroma().get_collection(collection_name)


def get_or_create_collection(collection_name: str):
    return _get_chroma().get_or_create_collection(collection_name)


# ── Retrieval ─────────────────────────────────────────────────────────────────

_APPROX_TOKENS_PER_CHAR = 0.25  # rough estimate; 1 token ≈ 4 chars


def _estimate_tokens(text: str) -> int:
    return int(len(text) * _APPROX_TOKENS_PER_CHAR)


def retrieve(
    collection_name: str,
    queries: list[str],
    top_k: int | None = None,
    token_budget: int = 1500,
) -> list[dict]:
    """
    Multi-query retrieval:
      1. Embed each query.
      2. Retrieve top_k chunks per query.
      3. De-duplicate by chunk_id.
      4. Cap to token_budget before returning.

    Returns list of {chunk_id, text, metadata}.
    """
    if top_k is None:
        top_k = settings.RETRIEVAL_TOP_K

    if not collection_exists(collection_name):
        logger.warning("Collection %r not found — returning empty context.", collection_name)
        return []

    collection = get_collection(collection_name)
    seen_ids: set[str] = set()
    merged: list[dict] = []

    for query in queries:
        query_embedding = embed(query)
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count()),
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            logger.warning("Retrieval query failed: %s", exc)
            continue

        for chunk_id, doc, meta in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
        ):
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                merged.append({"chunk_id": chunk_id, "text": doc, "metadata": meta})

    # Apply token budget — keep highest-ranked chunks first
    budget_used = 0
    within_budget = []
    for chunk in merged:
        tokens = _estimate_tokens(chunk["text"])
        if budget_used + tokens > token_budget:
            break
        within_budget.append(chunk)
        budget_used += tokens

    return within_budget
