import base64

from agno.agent import Agent
from loguru import logger
from openai import AsyncAzureOpenAI

from agent.exceptions import ExtractionError
from agent.llm import get_model
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
        model=get_model(),
        instructions=[EXTRACTION_SYSTEM],
        output_schema=PurchaseOrderExtraction,
        telemetry=False,
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
    """Extract PO data from scanned page images using Azure OpenAI vision."""
    client = AsyncAzureOpenAI(
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
    )

    content_blocks: list[dict] = []
    for img_bytes in images:
        content_blocks.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(img_bytes).decode()}",
                },
            }
        )
    content_blocks.append({"type": "text", "text": OCR_USER})

    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": OCR_SYSTEM},
            {"role": "user", "content": content_blocks},
        ],
    )

    response_text = response.choices[0].message.content
    logger.bind(step="extraction").debug("OCR response: {}", response_text)

    # Use the Agno agent to structure the OCR output
    agent = Agent(
        model=get_model(),
        instructions=[EXTRACTION_SYSTEM],
        output_schema=PurchaseOrderExtraction,
        telemetry=False,
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
