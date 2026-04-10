import json

from agno.agent import Agent
from loguru import logger
from pydantic import BaseModel

from agent.llm import get_model
from agent.prompts import RAG_VALIDATION_SYSTEM, RAG_VALIDATION_USER
from models.enums import IssueSeverity, IssueTagType
from schemas.extraction import PurchaseOrderExtraction
from schemas.validation import IssueTagResult
from services.knowledge import knowledge_service


class RAGTagAdjustment(BaseModel):
    original_tag: str
    action: str  # "keep", "upgrade", "downgrade", "remove"
    adjusted_severity: str | None = None
    reasoning: str


class RAGNewTag(BaseModel):
    tag: str
    severity: str
    description: str
    reasoning: str


class RAGValidationResult(BaseModel):
    adjustments: list[RAGTagAdjustment]
    new_tags: list[RAGNewTag]
    summary: str


async def rag_validate(
    extraction: PurchaseOrderExtraction,
    initial_tags: list[IssueTagResult],
    deterministic_details: dict,
) -> RAGValidationResult:
    """Use RAG knowledge base to review and refine validation tags."""
    knowledge = knowledge_service.get_knowledge()
    if not knowledge:
        logger.warning("RAG knowledge base not available — skipping RAG validation")
        return RAGValidationResult(
            adjustments=[
                RAGTagAdjustment(
                    original_tag=t.tag.value, action="keep", reasoning="RAG unavailable"
                )
                for t in initial_tags
            ],
            new_tags=[],
            summary="RAG knowledge base not available — all tags kept as-is",
        )

    agent = Agent(
        model=get_model(),
        knowledge=knowledge,
        search_knowledge=True,
        instructions=[RAG_VALIDATION_SYSTEM],
        output_schema=RAGValidationResult,
        telemetry=False,
    )

    prompt = RAG_VALIDATION_USER.format(
        extraction=extraction.model_dump_json(indent=2),
        initial_tags=json.dumps([t.model_dump() for t in initial_tags], indent=2, default=str),
        deterministic_details=json.dumps(deterministic_details, indent=2, default=str),
    )

    response = await agent.arun(prompt)
    result = response.content
    logger.bind(step="rag_validation").info(
        "RAG validation: {} adjustments, {} new tags, summary={}",
        len(result.adjustments),
        len(result.new_tags),
        result.summary[:100],
    )
    return result


def apply_rag_adjustments(
    initial_tags: list[IssueTagResult],
    rag_result: RAGValidationResult,
) -> list[IssueTagResult]:
    """Apply RAG adjustments to the initial tag list. Returns the final tag list."""
    # Build a lookup of adjustments by tag name
    adjustments_by_tag: dict[str, RAGTagAdjustment] = {}
    for adj in rag_result.adjustments:
        adjustments_by_tag[adj.original_tag] = adj

    final_tags: list[IssueTagResult] = []

    for tag in initial_tags:
        adj = adjustments_by_tag.get(tag.tag.value)
        if not adj:
            # No adjustment — keep as-is
            final_tags.append(tag)
            continue

        action = adj.action.lower().strip()

        if action == "remove":
            logger.bind(step="rag_validation").info(
                "RAG removed tag {}: {}", tag.tag.value, adj.reasoning
            )
            continue

        if action == "upgrade" and adj.adjusted_severity:
            try:
                new_severity = IssueSeverity(adj.adjusted_severity.upper())
                final_tags.append(
                    IssueTagResult(
                        tag=tag.tag,
                        severity=new_severity,
                        description=f"{tag.description} [RAG: {adj.reasoning}]",
                    )
                )
                logger.bind(step="rag_validation").info(
                    "RAG upgraded tag {} to {}: {}", tag.tag.value, new_severity, adj.reasoning
                )
            except ValueError:
                final_tags.append(tag)
            continue

        if action == "downgrade" and adj.adjusted_severity:
            try:
                new_severity = IssueSeverity(adj.adjusted_severity.upper())
                final_tags.append(
                    IssueTagResult(
                        tag=tag.tag,
                        severity=new_severity,
                        description=f"{tag.description} [RAG: {adj.reasoning}]",
                    )
                )
                logger.bind(step="rag_validation").info(
                    "RAG downgraded tag {} to {}: {}", tag.tag.value, new_severity, adj.reasoning
                )
            except ValueError:
                final_tags.append(tag)
            continue

        # "keep" or unrecognized action — keep original
        final_tags.append(tag)

    # Add new tags from RAG
    for new_tag in rag_result.new_tags:
        try:
            tag_type = IssueTagType(new_tag.tag.upper())
            severity = IssueSeverity(new_tag.severity.upper())
            final_tags.append(
                IssueTagResult(
                    tag=tag_type,
                    severity=severity,
                    description=f"{new_tag.description} [RAG: {new_tag.reasoning}]",
                )
            )
            logger.bind(step="rag_validation").info(
                "RAG added new tag {}/{}: {}", new_tag.tag, new_tag.severity, new_tag.description
            )
        except ValueError:
            logger.bind(step="rag_validation").warning(
                "RAG suggested unknown tag type or severity: {}/{}", new_tag.tag, new_tag.severity
            )

    return final_tags
