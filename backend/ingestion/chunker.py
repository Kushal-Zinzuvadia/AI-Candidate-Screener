"""
Text chunker for knowledge base ingestion (§6.2).

Strategy: recursive paragraph-boundary splitting at ~500 tokens with ~75-token
overlap. We prefer splitting on paragraph breaks over hard token cuts because it
preserves semantic units (a paragraph about "dropout" stays whole rather than
being split mid-sentence across two chunks).

Design decision: tiktoken cl100k_base is used for token counting — it's the
same tokenizer as Claude/GPT-4 so the chunk sizes are accurate for the models
we're using.
"""
import uuid
from typing import Optional

import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def chunk_text(
    text: str,
    source_title: str,
    role: str,
    section: str = "",
    page_number: Optional[int] = None,
    chunk_size: int = 500,
    overlap_tokens: int = 75,
) -> list[dict]:
    """
    Split text into overlapping chunks, each with metadata.

    Returns a list of dicts:
      {chunk_id, text, metadata: {role, source_title, section, page_number}}
    """
    # Split into paragraphs first
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[dict] = []
    current_paras: list[str] = []
    current_tokens: int = 0

    def flush(paras: list[str]) -> dict:
        chunk_text = "\n\n".join(paras)
        return {
            "chunk_id": f"{role}_{uuid.uuid4().hex[:12]}",
            "text": chunk_text,
            "metadata": {
                "role": role,
                "source_title": source_title,
                "section": section,
                "page_number": page_number or 0,
                "chunk_size_tokens": _count_tokens(chunk_text),
            },
        }

    for para in raw_paragraphs:
        para_tokens = _count_tokens(para)

        # If a single paragraph exceeds chunk_size, hard-split it by sentences
        if para_tokens > chunk_size:
            sentences = para.replace(". ", ".\n").split("\n")
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                sent_tokens = _count_tokens(sent)
                if current_tokens + sent_tokens > chunk_size and current_paras:
                    chunks.append(flush(current_paras))
                    # Keep overlap from tail of current chunk
                    overlap_paras, overlap_tok = [], 0
                    for prev in reversed(current_paras):
                        t = _count_tokens(prev)
                        if overlap_tok + t <= overlap_tokens:
                            overlap_paras.insert(0, prev)
                            overlap_tok += t
                        else:
                            break
                    current_paras = overlap_paras
                    current_tokens = overlap_tok
                current_paras.append(sent)
                current_tokens += sent_tokens
            continue

        if current_tokens + para_tokens > chunk_size and current_paras:
            chunks.append(flush(current_paras))
            # Overlap: keep last few paragraphs within overlap budget
            overlap_paras, overlap_tok = [], 0
            for prev in reversed(current_paras):
                t = _count_tokens(prev)
                if overlap_tok + t <= overlap_tokens:
                    overlap_paras.insert(0, prev)
                    overlap_tok += t
                else:
                    break
            current_paras = overlap_paras
            current_tokens = overlap_tok

        current_paras.append(para)
        current_tokens += para_tokens

    if current_paras:
        chunks.append(flush(current_paras))

    return chunks
