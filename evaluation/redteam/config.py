"""
Configuration for the PyRIT red-team engine (ported from Jatinder's evaluation
branch, rewired to our conventions).

Two model roles:
  - Objective/target = the water-permit backend (`/invoke`), the system under attack.
  - Adversarial = the attack-generating model. We default it to the same GPT-5.1
    Azure AI Foundry deployment used as our eval judge, authenticated with
    Azure AD (`az login`) — leave ADVERSARIAL_API_KEY unset to use AAD.

All values come from evaluation/.env (see .env.example).
"""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- Objective/eval model (also default adversarial) --------------------
    azure_openai_endpoint: str = Field(default="", validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", validation_alias="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(
        default="2025-04-01-preview", validation_alias="AZURE_OPENAI_API_VERSION"
    )
    azure_openai_deployment: str = Field(
        default="gpt-5.1",
        validation_alias=AliasChoices(
            "FOUNDRY_MODEL", "AZURE_OPENAI_DEPLOYMENT", "azure_openai_chat_deployment_name"
        ),
    )

    # ---- Adversarial (attack-generation) model ------------------------------
    # Falls back to the objective model config when unset. Leave the API key
    # empty to authenticate with Azure AD (az login).
    adversarial_endpoint: str = Field(default="", validation_alias="ADVERSARIAL_ENDPOINT")
    adversarial_api_key: str = Field(default="", validation_alias="ADVERSARIAL_API_KEY")
    adversarial_deployment: str = Field(default="", validation_alias="ADVERSARIAL_DEPLOYMENT")
    adversarial_api_version: str = Field(default="", validation_alias="ADVERSARIAL_API_VERSION")

    # ---- Backend (objective target) -----------------------------------------
    backend_api_url: str = Field(
        default="http://localhost:8002", validation_alias="BACKEND_API_URL"
    )
    backend_api_timeout: int = Field(default=60, validation_alias="BACKEND_API_TIMEOUT")

    # ---- Red-team run configuration -----------------------------------------
    red_team_threat_models: str = Field(
        default="jailbreak,prompt_injection,data_exfiltration",
        validation_alias="RED_TEAM_THREAT_MODELS",
    )
    red_team_max_iterations: int = Field(
        default=5, validation_alias="RED_TEAM_MAX_ITERATIONS"
    )
    red_team_timeout_seconds: int = Field(
        default=300, validation_alias="RED_TEAM_TIMEOUT_SECONDS"
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )


settings = Settings()
