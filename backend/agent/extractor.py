import base64

from agno.agent import Agent
from agno.models.anthropic import Claude
from anthropic import AsyncAnthropic
from loguru import logger

from agent.exceptions import ExtractionError
from agent.prompts import EXTRACTION_SYSTEM, EXTRACTION_USER, OCR_SYSTEM, OCR_USER
from core.config import settings
from schemas.extraction import PurchaseOrderExtraction


async def extract_po_data(
    content: str | None = None,
    images: list[bytes] | None = None,
) -> PurchaseOrderExtraction:
    """Extract structured PO data from text content or scanned images."""
    try:
        if images:
            return await _extract_from_images(images)
        if content:
            return await _extract_from_text(content)
        raise ExtractionError("No content or images provided for extraction")
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"Data extraction failed: {exc}") from exc


async def _extract_from_text(content: str) -> PurchaseOrderExtraction:
    """Extract PO data from text content using Agno agent."""
    agent = Agent(
        model=Claude(id="claude-sonnet-4-5", api_key=settings.anthropic_api_key),
        instructions=[EXTRACTION_SYSTEM],
        response_model=PurchaseOrderExtraction,
    )
    prompt = EXTRACTION_USER.format(content=content)
    response = await agent.arun(prompt)
    result = response.content
    logger.bind(step="extraction").info(
        "Extracted PO: po_number={}, vendor={}, items={}",
        result.po_number,
        result.vendor.name,
        len(result.line_items),
    )
    return result


async def _extract_from_images(images: list[bytes]) -> PurchaseOrderExtraction:
    """Extract PO data from scanned page images using Claude vision."""
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    content_blocks: list[dict] = []
    for img_bytes in images:
        content_blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(img_bytes).decode(),
                },
            }
        )
    content_blocks.append({"type": "text", "text": OCR_USER})

    response = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=OCR_SYSTEM,
        messages=[{"role": "user", "content": content_blocks}],
    )

    # Parse the response text as PurchaseOrderExtraction
    response_text = response.content[0].text
    logger.bind(step="extraction").debug("OCR response: {}", response_text)

    # Use the Agno agent to structure the OCR output
    agent = Agent(
        model=Claude(id="claude-sonnet-4-5", api_key=settings.anthropic_api_key),
        instructions=[EXTRACTION_SYSTEM],
        response_model=PurchaseOrderExtraction,
    )
    structured = await agent.arun(
        f"Structure this OCR output into the required JSON format:\n\n{response_text}"
    )
    result = structured.content
    logger.bind(step="extraction").info(
        "Extracted PO from scan: po_number={}, vendor={}, items={}",
        result.po_number,
        result.vendor.name,
        len(result.line_items),
    )
    return result
