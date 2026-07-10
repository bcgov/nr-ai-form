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

    # Azure AI Search Configuration
    azure_search_endpoint: str = Field(
        default="",
        validation_alias="AZURE_SEARCH_ENDPOINT",
    )
    azure_search_api_key: str = Field(
        default="",
        validation_alias="AZURE_SEARCH_API_KEY",
    )
    azure_search_index_name: str = Field(
        default="",
        validation_alias="AZURE_SEARCH_INDEX_NAME",
    )
    azure_search_top: int = Field(
        default=3,
        validation_alias="AZURE_SEARCH_TOP",
    )
    azure_search_trim_length: int = Field(
        default=500,
        validation_alias="AZURE_SEARCH_TRIM_LENGTH",
    )
    azure_search_enable_trimming: bool = Field(
        default=True,
        validation_alias="AZURE_SEARCH_ENABLE_TRIMMING",
    )
    azure_search_include_total_count: bool = Field(
        default=True,
        validation_alias="AZURE_SEARCH_INCLUDE_TOTAL_COUNT",
    )
    azure_search_query_type: str = Field(
        default="simple",
        validation_alias="AZURE_SEARCH_QUERY_TYPE",
    )
    azure_search_semantic_configuration: str = Field(
        default="default",
        validation_alias="AZURE_SEARCH_SEMANTIC_CONFIGURATION",
    )
    azure_search_query_caption: str = Field(
        default="extractive",
        validation_alias="AZURE_SEARCH_QUERY_CAPTION",
    )
    azure_search_query_answer: str = Field(
        default="extractive",
        validation_alias="AZURE_SEARCH_QUERY_ANSWER",
    )
    azure_search_query_answer_count: int = Field(
        default=3,
        validation_alias="AZURE_SEARCH_QUERY_ANSWER_COUNT",
    )
    azure_search_query_language: str = Field(
        default="en-us",
        validation_alias="AZURE_SEARCH_QUERY_LANGUAGE",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # prevents crash if env contains keys we don't model
    )
    groundedness_threshold: float = Field(
        default=0.5,
        validation_alias="GROUNDEDNESS_THRESHOLD",
    )
    
    code_vulnerability_threshold: float = Field(
        default=0.8,
        validation_alias="CODE_VULNERABILITY_THRESHOLD",
    )

    # PyRIT Red-Teaming Configuration
    enable_red_team: bool = Field(
        default=False,
        validation_alias="ENABLE_RED_TEAM",
    )
    
    red_team_threat_models: str = Field(
        default="jailbreak,prompt_injection,data_exfiltration",
        validation_alias="RED_TEAM_THREAT_MODELS",
    )  # Comma-separated list of threat models to test
    
    red_team_max_iterations: int = Field(
        default=5,
        validation_alias="RED_TEAM_MAX_ITERATIONS",
    )  # Max attack chains per threat model
    
    red_team_timeout_seconds: int = Field(
        default=300,
        validation_alias="RED_TEAM_TIMEOUT_SECONDS",
    )  # Timeout per red-team test
    
    red_team_vulnerability_threshold: float = Field(
        default=0.3,
        validation_alias="RED_TEAM_VULNERABILITY_THRESHOLD",
    )  # Score above this = vulnerable

    def validate_config(self) -> bool:
        """Validate required configuration"""
        if not self.azure_openai_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is required")
        if not self.azure_openai_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is required")
        if not self.backend_api_url:
            raise ValueError("BACKEND_API_URL is required")
        return True

    def use_azure_search(self) -> bool:
        """Check if Azure Search is configured."""
        return bool(
            self.azure_search_endpoint
            and self.azure_search_api_key
            and self.azure_search_index_name
        )


# Global settings instance
settings = Settings()
