from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str
    github_token: str
    github_webhook_secret: str
    qdrant_url: str = ":memory:"
    embedding_model: str = "text-embedding-3-small"
    review_model: str = "claude-3-5-sonnet-20241022"

    model_config = {"env_file": ".env"}


settings = Settings()