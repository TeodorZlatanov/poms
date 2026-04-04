import asyncio
import contextlib
import io

import pandas as pd

# Activate GNN-based layout detection BEFORE importing pymupdf4llm — order is mandatory
with contextlib.suppress(ImportError):
    import pymupdf.layout  # noqa: F401

import pymupdf
import pymupdf4llm

from agent.exceptions import FileProcessingError


def detect_file_type(filename: str, content_type: str, data: bytes) -> str:
    """Detect file type. Returns 'pdf_digital', 'pdf_scanned', 'csv', or 'image'."""
    lower_name = filename.lower()
    lower_ct = content_type.lower()

    # CSV detection
    if lower_ct == "text/csv" or lower_name.endswith(".csv"):
        return "csv"

    # Image detection
    if lower_ct.startswith("image/") or lower_name.endswith((".png", ".jpg", ".jpeg", ".tiff")):
        return "image"

    # PDF detection — check if pages have extractable text
    if lower_ct == "application/pdf" or lower_name.endswith(".pdf"):
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
            total_text = ""
            for page in doc:
                total_text += page.get_text().strip()
            doc.close()
            if len(total_text) < 50:
                return "pdf_scanned"
            return "pdf_digital"
        except Exception as exc:
            raise FileProcessingError(f"Failed to analyze PDF: {exc}") from exc

    raise FileProcessingError(f"Unsupported file type: {content_type} ({filename})")


async def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a digital PDF using pymupdf4llm."""

    def _extract() -> str:
        doc = pymupdf.open(stream=data, filetype="pdf")
        md_text = pymupdf4llm.to_markdown(doc)
        doc.close()
        return md_text

    return await asyncio.to_thread(_extract)


async def extract_images_from_pdf(data: bytes) -> list[bytes]:
    """Render each page of a scanned PDF to a PNG image at 300 DPI."""

    def _render() -> list[bytes]:
        doc = pymupdf.open(stream=data, filetype="pdf")
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            images.append(pix.tobytes("png"))
        doc.close()
        return images

    return await asyncio.to_thread(_render)


async def extract_text_from_csv(data: bytes) -> str:
    """Parse CSV data and return a readable string representation."""

    def _parse() -> str:
        df = pd.read_csv(io.BytesIO(data))
        return df.to_string(index=False)

    return await asyncio.to_thread(_parse)
