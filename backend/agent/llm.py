from agno.models.azure.openai_chat import AzureOpenAI

from core.config import settings


def get_model() -> AzureOpenAI:
    """Return the Azure OpenAI model used by every agent (classification,
    extraction, RAG validation)."""
    return AzureOpenAI(
        id=settings.azure_openai_deployment,
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
    )
