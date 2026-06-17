"""Configuration management for evaluation application."""

from __future__ import annotations

from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Azure OpenAI Configuration
    azure_openai_api_key: str = Field(default="", validation_alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(default="", validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        validation_alias="AZURE_OPENAI_API_VERSION",
    )
    # Accept both env names:
    # - AZURE_OPENAI_DEPLOYMENT (our .env.example)
    # - azure_openai_chat_deployment_name (common in Azure AI SDK samples)
    azure_openai_deployment: str = Field(
        default="gpt-4",
        validation_alias=AliasChoices(
            "AZURE_OPENAI_DEPLOYMENT", "azure_openai_chat_deployment_name"
        ),
    )

    # Backend API Configuration
    backend_api_url: str = Field(
        default="http://localhost:8000",
        validation_alias="BACKEND_API_URL",
    )
    backend_api_timeout: int = Field(default=30, validation_alias="BACKEND_API_TIMEOUT")

    # Evaluation Configuration
    evaluation_run_name: str = Field(
        default="evaluation_run",
        validation_alias="EVALUATION_RUN_NAME",
    )
    evaluation_scenario: str = Field(
        default="basic_evaluation",
        validation_alias="EVALUATION_SCENARIO",
    )

    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # Evaluator Configuration
    enabled_evaluators: str = Field(
        default="groundedness",
        validation_alias="ENABLED_EVALUATORS",
    )  # Comma-separated list of evaluator names to run

    # Azure AI Project Configuration (required for ViolenceEvaluator)
    azure_ai_project: Optional[str] = Field(
        default="https://ai-services-hub-test-foundry.services.ai.azure.com/api/projects/wlrs-water-form-assistant-project",
        validation_alias="AZURE_AI_PROJECT",
    )  # Azure AI project endpoint URL or connection string

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # prevents crash if env contains keys we don't model
    )
    groundedness_threshold: float = Field(
        default=0.5,
        validation_alias="GROUNDEDNESS_THRESHOLD",
    )

    def validate_config(self) -> bool:
        """Validate required configuration"""
        if not self.azure_openai_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is required")
        if not self.azure_openai_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is required")
        if not self.backend_api_url:
            raise ValueError("BACKEND_API_URL is required")
        return True


# Global settings instance
settings = Settings()
