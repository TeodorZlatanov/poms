from agno.agent import Agent
from agno.models.anthropic import Claude
from loguru import logger
from pydantic import BaseModel

from agent.exceptions import ClassificationError
from agent.prompts import CLASSIFICATION_SYSTEM, CLASSIFICATION_USER
from core.config import settings


class ClassificationResult(BaseModel):
    is_purchase_order: bool
    reasoning: str


async def classify_email(
    subject: str,
    body: str,
    filenames: list[str],
) -> bool:
    """Returns True if the email contains a purchase order."""
    try:
        agent = Agent(
            model=Claude(id="claude-haiku-3-5", api_key=settings.anthropic_api_key),
            instructions=[CLASSIFICATION_SYSTEM],
            response_model=ClassificationResult,
        )
        prompt = CLASSIFICATION_USER.format(
            subject=subject,
            body=body,
            filenames=", ".join(filenames) if filenames else "none",
        )
        response = await agent.arun(prompt)
        result = response.content
        logger.bind(step="classification").info(
            "Classification result: is_po={}, reason={}", result.is_purchase_order, result.reasoning
        )
        return result.is_purchase_order
    except Exception as exc:
        raise ClassificationError(f"Email classification failed: {exc}") from exc
