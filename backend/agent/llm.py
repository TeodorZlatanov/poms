from agno.models.azure.openai_chat import AzureOpenAI

from core.config import settings


def get_model() -> AzureOpenAI:
    """Return the primary Azure OpenAI model (GPT-4.1) for extraction and RAG."""
    return AzureOpenAI(
        id=settings.azure_openai_deployment,
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
    )


def get_small_model() -> AzureOpenAI:
    """Return a lighter Azure OpenAI model for classification."""
    return AzureOpenAI(
        id=settings.azure_openai_deployment_small,
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
    )
