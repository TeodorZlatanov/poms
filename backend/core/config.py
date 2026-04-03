from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://poms:poms_dev_password@localhost:5432/poms"

    # LLM
    anthropic_api_key: str = ""

    # Gmail
    gmail_credentials_path: str = "./credentials.json"
    gmail_token_path: str = "./token.json"
    agent_email: str = "po.processing.demo@gmail.com"

    # Embeddings
    embedding_provider: str = "openai"
    openai_api_key: str = ""

    # Knowledge base
    lancedb_path: str = "./data/lancedb"

    # Application
    poll_interval_seconds: int = 30
    log_level: str = "INFO"
    log_path: str = "./logs"
    debug: bool = False


settings = Settings()
