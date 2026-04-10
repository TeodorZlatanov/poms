from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://poms:poms_dev_password@localhost:5432/poms"

    # Azure OpenAI — Completion
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = ""
    azure_openai_deployment: str = ""

    # Azure OpenAI — Embeddings
    azure_openai_embed_api_key: str = ""
    azure_openai_embed_endpoint: str = ""
    azure_openai_embed_deployment: str = ""
    azure_openai_embed_dimensions: int = 3072

    # Gmail
    gmail_credentials_path: str = "./credentials.json"
    gmail_token_path: str = "./token.json"
    agent_email: str = ""

    # Knowledge base
    lancedb_path: str = "./data/lancedb"
    knowledge_pdf_dir: str = "../../knowledge/pdfs"

    # Application
    poll_interval_seconds: int = 30
    log_level: str = "INFO"
    log_path: str = "./logs"
    debug: bool = False


settings = Settings()
