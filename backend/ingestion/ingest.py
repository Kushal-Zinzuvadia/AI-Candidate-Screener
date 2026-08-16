"""
Knowledge base ingestion CLI (§6.2).

Usage:
  python ingestion/ingest.py --role ai_ml
  python ingestion/ingest.py --role data_science
  python ingestion/ingest.py --role ai_ml --source ingestion/kb_sources/ai_ml/

Reads all .txt, .md, and .pdf files from the source directory, chunks them,
embeds them with sentence-transformers, and writes to a ChromaDB collection
named `kb_{role}`.

Run this ONCE before starting the server. It is not part of the request path.
"""
import argparse
import os
import sys
from pathlib import Path

# Allow imports from backend root when running as CLI
sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz  # PyMuPDF
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from ingestion.chunker import chunk_text

ROLES = {
    "ai_ml": {
        "collection": "kb_ai_ml",
        "source_default": Path(__file__).parent / "kb_sources" / "ai_ml",
        "display": "AI/ML Engineer",
    },
    "data_science": {
        "collection": "kb_data_science",
        "source_default": Path(__file__).parent / "kb_sources" / "data_science",
        "display": "Data Science / Applied ML",
    },
}

CHUNK_SIZE = 500
OVERLAP = 75
BATCH_SIZE = 64  # ChromaDB upsert batch size


def extract_text_from_file(path: Path) -> tuple[str, list[tuple[str, int]]]:
    """
    Returns (full_text, [(section_text, page_number)]).
    For plain text files, all content is page 1.
    """
    ext = path.suffix.lower()
    if ext == ".pdf":
        doc = fitz.open(str(path))
        pages = []
        for i, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                pages.append((text, i))
        return "\n\n".join(t for t, _ in pages), pages
    elif ext in {".txt", ".md"}:
        content = path.read_text(encoding="utf-8", errors="ignore")
        # Split by markdown headers as sections
        sections = []
        current: list[str] = []
        for line in content.splitlines():
            if line.startswith("#") and current:
                sections.append(("\n".join(current), 1))
                current = [line]
            else:
                current.append(line)
        if current:
            sections.append(("\n".join(current), 1))
        return content, sections
    else:
        return "", []


def ingest(role_key: str, source_dir: Path, chroma_persist_dir: str, embedding_model_name: str):
    role_cfg = ROLES[role_key]
    collection_name = role_cfg["collection"]

    print(f"\n{'='*60}")
    print(f"Ingesting role: {role_cfg['display']}")
    print(f"Source: {source_dir}")
    print(f"Collection: {collection_name}")
    print(f"{'='*60}\n")

    # Load embedding model
    print("Loading embedding model...")
    model = SentenceTransformer(embedding_model_name)

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_persist_dir)

    # Delete existing collection if present (fresh ingest)
    try:
        client.delete_collection(collection_name)
        print(f"Deleted existing collection '{collection_name}'.")
    except Exception:
        pass
    collection = client.create_collection(collection_name)

    # Find source files
    files = list(source_dir.glob("**/*.pdf")) + list(source_dir.glob("**/*.txt")) + list(source_dir.glob("**/*.md"))
    if not files:
        print(f"ERROR: No .pdf/.txt/.md files found in {source_dir}")
        sys.exit(1)

    all_chunks: list[dict] = []
    for file_path in files:
        print(f"Processing: {file_path.name}")
        full_text, sections = extract_text_from_file(file_path)
        if not full_text.strip():
            print(f"  Skipped (empty).")
            continue

        file_chunks = []
        # Detect section header from text
        section_name = ""
        for section_text, page_num in sections:
            lines = section_text.strip().splitlines()
            if lines and lines[0].startswith("#"):
                section_name = lines[0].lstrip("#").strip()
            chunks = chunk_text(
                text=section_text,
                source_title=file_path.stem.replace("_", " ").title(),
                role=role_key,
                section=section_name,
                page_number=page_num,
                chunk_size=CHUNK_SIZE,
                overlap_tokens=OVERLAP,
            )
            file_chunks.extend(chunks)

        print(f"  → {len(file_chunks)} chunks")
        all_chunks.extend(file_chunks)

    if not all_chunks:
        print("No chunks generated. Check source files.")
        sys.exit(1)

    # Embed + upsert in batches
    print(f"\nEmbedding {len(all_chunks)} chunks...")
    for i in tqdm(range(0, len(all_chunks), BATCH_SIZE)):
        batch = all_chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        ids = [c["chunk_id"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()
        collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

    print(f"\n✓ Done! {len(all_chunks)} chunks written to '{collection_name}'.")
    print(f"  Collection count: {collection.count()}")


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge base into ChromaDB.")
    parser.add_argument("--role", required=True, choices=list(ROLES.keys()), help="Role key to ingest.")
    parser.add_argument("--source", type=str, default=None, help="Override source directory path.")
    parser.add_argument("--chroma-dir", type=str, default="./chroma_data", help="ChromaDB persist directory.")
    parser.add_argument("--embedding-model", type=str, default="all-MiniLM-L6-v2", help="Sentence-transformer model.")
    args = parser.parse_args()

    source_dir = Path(args.source) if args.source else ROLES[args.role]["source_default"]
    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}")
        sys.exit(1)

    ingest(
        role_key=args.role,
        source_dir=source_dir,
        chroma_persist_dir=args.chroma_dir,
        embedding_model_name=args.embedding_model,
    )


if __name__ == "__main__":
    main()
