"""Ingest knowledge PDFs into the LanceDB vector database.

Processes all PDFs in the knowledge/pdfs/ directory:
  PDF → pymupdf4llm (markdown with layout detection) → MarkdownHeaderTextSplitter
  → merge sub-section chunks → embed with Azure OpenAI → insert into LanceDB

Usage:
    cd backend && uv run python -m scripts.ingest_knowledge
    cd backend && uv run python -m scripts.ingest_knowledge --pdf-dir ../knowledge/pdfs
    cd backend && uv run python -m scripts.ingest_knowledge --drop  # recreate from scratch
"""

import argparse
import contextlib
import hashlib
import time
from pathlib import Path

# Activate GNN-based layout detection BEFORE importing pymupdf4llm — order is mandatory
with contextlib.suppress(ImportError):
    import pymupdf.layout  # noqa: F401

import pymupdf
import pymupdf4llm
from agno.knowledge.document.base import Document as AgnoDocument
from agno.knowledge.embedder.azure_openai import AzureOpenAIEmbedder
from agno.vectordb.lancedb.lance_db import LanceDb
from agno.vectordb.search import SearchType
from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter

from core.config import settings


def get_embedder() -> AzureOpenAIEmbedder:
    return AzureOpenAIEmbedder(
        azure_endpoint=settings.azure_openai_embed_endpoint,
        api_key=settings.azure_openai_embed_api_key,
        azure_deployment=settings.azure_openai_embed_deployment,
        dimensions=settings.azure_openai_embed_dimensions,
    )


def process_pdf(pdf_path: Path) -> list[AgnoDocument]:
    """Extract markdown from a PDF, chunk by section, return Agno documents."""
    print(f"  Processing {pdf_path.name}...")
    t0 = time.perf_counter()

    doc = pymupdf.open(str(pdf_path))
    md = pymupdf4llm.to_markdown(
        doc,
        page_chunks=True,
        use_ocr=True,
        show_progress=False,
    )
    doc.close()

    # Handle return type
    if isinstance(md, str):
        full_text = md
    else:
        full_text = "\n\n".join(
            page["text"] for page in md if isinstance(page, dict) and "text" in page
        )

    # Split by markdown headers
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ],
        strip_headers=False,
    )
    raw_chunks = splitter.split_text(full_text)

    # Merge sub-section chunks into parent numbered sections
    merged = _merge_section_chunks(raw_chunks)

    # Convert to Agno Documents
    agno_docs = []
    for lc_doc in merged:
        metadata = {
            **lc_doc.metadata,
            "source": pdf_path.name,
        }
        agno_docs.append(AgnoDocument(content=lc_doc.page_content, meta_data=metadata))

    elapsed = time.perf_counter() - t0
    print(f"    {len(raw_chunks)} raw chunks → {len(merged)} merged ({elapsed:.1f}s)")
    return agno_docs


def _get_parent_section(h2_value: str) -> str | None:
    """Extract numbered section prefix from an h2 value (e.g. '**2. Vendor...' → '2.')."""
    cleaned = h2_value.strip().strip("*").strip()
    if cleaned and cleaned[0].isdigit():
        dot_pos = cleaned.find(".")
        if dot_pos > 0:
            return cleaned[: dot_pos + 1]
    return None


def _merge_section_chunks(chunks: list) -> list:
    """Merge consecutive chunks that belong to the same numbered parent section.

    pymupdf4llm promotes bold text to ## headers, so a vendor profile like
    "2. Vendor Profile: TechParts..." gets fragmented into tiny chunks for
    "Contract Status: ACTIVE", "Known Name Variations:", etc.
    This merges those back into one chunk per numbered section.
    """
    if not chunks:
        return chunks

    merged: list = []
    current_section: str | None = None
    accumulator = None

    for chunk in chunks:
        h2 = chunk.metadata.get("h2", "")
        parent = _get_parent_section(h2)

        if parent is not None:
            if accumulator is not None:
                merged.append(accumulator)
            current_section = parent
            accumulator = chunk
        elif current_section is not None and accumulator is not None:
            accumulator.page_content += "\n\n" + chunk.page_content
        else:
            if accumulator is not None:
                merged.append(accumulator)
                accumulator = None
                current_section = None
            merged.append(chunk)

    if accumulator is not None:
        merged.append(accumulator)

    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest knowledge PDFs into LanceDB")
    parser.add_argument(
        "--pdf-dir",
        default=settings.knowledge_pdf_dir,
        help=f"Directory containing knowledge PDFs (default: {settings.knowledge_pdf_dir})",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing knowledge table and recreate from scratch",
    )
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.exists():
        print(f"ERROR: PDF directory not found: {pdf_dir}")
        return

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"ERROR: No PDF files found in {pdf_dir}")
        return

    print(f"Found {len(pdf_files)} PDFs in {pdf_dir}")

    # Process all PDFs
    all_chunks: list[AgnoDocument] = []
    for pdf_path in pdf_files:
        chunks = process_pdf(pdf_path)
        all_chunks.extend(chunks)

    print(f"\nTotal chunks to ingest: {len(all_chunks)}")

    # Create vectorstore
    print("Initializing embedder and LanceDB...")
    embedder = get_embedder()
    vectorstore = LanceDb(
        table_name="knowledge",
        uri=settings.lancedb_path,
        embedder=embedder,
        search_type=SearchType.hybrid,
    )

    if args.drop:
        try:
            if vectorstore.exists():
                print("Dropping existing knowledge table...")
                vectorstore.drop()
        except Exception:
            print("No existing table to drop — creating fresh")

    # Build a content hash from the PDF filenames for deduplication
    file_names = sorted(p.name for p in pdf_files)
    content_hash = hashlib.sha256("|".join(file_names).encode()).hexdigest()[:16]
    print(f"Content hash: {content_hash}")

    # Insert or upsert
    t0 = time.perf_counter()
    if vectorstore.exists():
        print("Table exists — upserting documents...")
        vectorstore.upsert(content_hash=content_hash, documents=all_chunks)
    else:
        print("Creating new knowledge table...")
        vectorstore.insert(content_hash=content_hash, documents=all_chunks)

    elapsed = time.perf_counter() - t0
    print(f"Ingestion complete in {elapsed:.1f}s")
    print(f"Knowledge base ready at {settings.lancedb_path}/knowledge")


if __name__ == "__main__":
    main()
