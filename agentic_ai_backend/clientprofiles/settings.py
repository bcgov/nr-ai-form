"""Typed tenant settings derived from a ClientProfile document."""

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    ClientProfile,
    ConversationAgentConfig,
    FormSupportAgentConfig,
    OrchestratorRuntimeSettings,
)


class TenantSettingsValidationError(ValueError):
    """Raised when a Cosmos tenant profile is missing required runtime settings."""


class AgentSettings(BaseModel):
    """Shared shape sent from the orchestrator to a sub-agent."""

    model_config = ConfigDict(extra="allow")

    agentType: str
    enabled: bool = True
    clientId: str | None = None
    configFingerprint: str | None = None
    promptPath: str | None = None
    blobConnectionString: str | None = None
    containerName: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class ConversationAgentSettings(AgentSettings):
    agentType: Literal["conversationAgent"] = "conversationAgent"
    config: ConversationAgentConfig = Field(default_factory=ConversationAgentConfig)


class FormSupportAgentSettings(AgentSettings):
    agentType: Literal["formSupportAgent"] = "formSupportAgent"
    config: FormSupportAgentConfig = Field(default_factory=FormSupportAgentConfig)


class OrchestratorPromptSettings(BaseModel):
    """Tenant-specific prompt storage for dispatcher and aggregator prompts."""

    blobConnectionString: str | None = None
    containerName: str | None = None
    dispatcherPromptPath: str | None = None
    aggregatorPromptPath: str | None = None

    @property
    def prompt_directories(self) -> dict[str, str]:
        return {
            key: value
            for key, value in {
                "AGENT_DISPATCHER_PROMPTS_PATH": self.dispatcherPromptPath,
                "AGENT_AGGREGATOR_PROMPTS_PATH": self.aggregatorPromptPath,
            }.items()
            if value
        }


class TenantAgentSettings(BaseModel):
    client_id: str
    config_fingerprint: str
    conversation: ConversationAgentSettings
    form_support: FormSupportAgentSettings
    orchestrator_prompts: OrchestratorPromptSettings
    orchestrator_runtime: OrchestratorRuntimeSettings


def build_config_fingerprint(profile: ClientProfile) -> str:
    """Return a stable, secret-safe cache version for a tenant profile.

    The digest may change when secrets change, but raw secret values never appear
    in cache keys or logs.
    """
    payload = profile.model_dump(mode="json", exclude_none=True)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _is_missing(value: Any) -> bool:
    return value in (None, "")


def _require_value(value: Any, path: str) -> None:
    if _is_missing(value):
        raise TenantSettingsValidationError(f"{path} is required in tenant profile.")


def _require_agent_field(settings: AgentSettings, field_name: str, label: str) -> None:
    _require_value(getattr(settings, field_name), f"{label}.{field_name}")


def _require_config_field(config: BaseModel, field_name: str, label: str) -> None:
    _require_value(getattr(config, field_name), f"{label}.config.{field_name}")


def _validate_shared_blob_settings(settings: AgentSettings, label: str) -> None:
    _require_agent_field(settings, "blobConnectionString", label)
    _require_agent_field(settings, "containerName", label)
    _require_agent_field(settings, "promptPath", label)


def _validate_conversation(settings: ConversationAgentSettings) -> None:
    if not settings.enabled:
        return

    _validate_shared_blob_settings(settings, "conversationAgent")
    mode = settings.config.conversationAgentMode or "knowledgebase"
    settings.config.conversationAgentMode = mode

    if mode == "llm":
        for field_name in (
            "azureOpenaiEndpoint",
            "azureOpenaiApiKey",
            "azureOpenaiChatDeploymentName",
            "azureOpenaiApiVersion",
            "azureSearchEndpoint",
            "azureSearchApiKey",
            "azureSearchIndexName",
        ):
            _require_config_field(settings.config, field_name, "conversationAgent")
        return

    for field_name in (
        "azureSearchEndpoint",
        "azureSearchApiKey",
        "azureSearchKnowledgeAgentName",
    ):
        _require_config_field(settings.config, field_name, "conversationAgent")


def _validate_form_support(settings: FormSupportAgentSettings) -> None:
    if not settings.enabled:
        return

    _validate_shared_blob_settings(settings, "formSupportAgent")
    for field_name in (
        "formDefinitionContainer",
        "stepBasedPromptContainer",
        "azureOpenaiEndpoint",
        "azureOpenaiApiKey",
        "azureOpenaiChatDeploymentName",
        "azureOpenaiApiVersion",
    ):
        _require_config_field(settings.config, field_name, "formSupportAgent")


def _validate_orchestrator_prompts(settings: OrchestratorPromptSettings) -> None:
    for field_name in (
        "blobConnectionString",
        "containerName",
        "dispatcherPromptPath",
        "aggregatorPromptPath",
    ):
        _require_value(getattr(settings, field_name), f"orchestratorPrompts.{field_name}")


def _validate_orchestrator_runtime(settings: OrchestratorRuntimeSettings) -> None:
    for field_name in (
        "azureOpenAIEndpoint",
        "azureOpenAIChatDeploymentName",
        "azureOpenAIApiVersion",
        "azureOpenAIApiKey",
        "azureOpenAIAggregatorChatDeploymentName",
        "azureOpenAIAggregatorMaxCompletionTokens",
        "formStepNumber",
        "a2aClientTimeoutSeconds",
    ):
        _require_value(getattr(settings, field_name), f"tenantResources.config.{field_name}")


def build_tenant_agent_settings(profile: ClientProfile) -> TenantAgentSettings:
    """Convert the flexible Cosmos profile into typed, validated runtime settings."""
    # TODO: Resolve Key Vault secret references or managed-identity-backed resources
    # before model validation. Cosmos should store non-secret config and secret
    # references, not raw API keys or connection strings.
    profile_data = profile.model_dump()
    tenant_resources = profile_data.get("tenantResources") or {}
    subagents = profile_data.get("subAgents") or []
    fingerprint = build_config_fingerprint(profile)

    def subagent(agent_type: str) -> dict[str, Any]:
        raw = next((item for item in subagents if item.get("agentType") == agent_type), {})
        # Shared blob fields are flattened because current sub-agent invoke contracts expect them there.
        return {
            **tenant_resources,
            **raw,
            "clientId": profile.clientId,
            "configFingerprint": fingerprint,
        }

    prompts = tenant_resources.get("prompts") or {}
    runtime_config = tenant_resources.get("config") or {}
    settings = TenantAgentSettings(
        client_id=profile.clientId,
        config_fingerprint=fingerprint,
        conversation=ConversationAgentSettings.model_validate(subagent("conversationAgent")),
        form_support=FormSupportAgentSettings.model_validate(subagent("formSupportAgent")),
        orchestrator_prompts=OrchestratorPromptSettings(
            blobConnectionString=tenant_resources.get("blobConnectionString"),
            containerName=tenant_resources.get("containerName"),
            dispatcherPromptPath=prompts.get("dispatcher"),
            aggregatorPromptPath=prompts.get("aggregator"),
        ),
        orchestrator_runtime=OrchestratorRuntimeSettings.model_validate(runtime_config),
    )

    _validate_conversation(settings.conversation)
    _validate_form_support(settings.form_support)
    _validate_orchestrator_prompts(settings.orchestrator_prompts)
    _validate_orchestrator_runtime(settings.orchestrator_runtime)
    return settings


def validate_client_profiles(raw_profiles: list[dict[str, Any]]) -> None:
    """Validate raw seed/profile documents using the runtime tenant settings rules."""
    errors: list[str] = []
    for index, raw_profile in enumerate(raw_profiles, start=1):
        client_id = raw_profile.get("clientId") or raw_profile.get("id") or f"profile #{index}"
        try:
            profile = ClientProfile.model_validate(raw_profile)
            build_tenant_agent_settings(profile)
        except Exception as exc:
            errors.append(f"- {client_id}: {exc}")

    if errors:
        details = "\n".join(errors)
        raise TenantSettingsValidationError(f"Tenant profile validation failed:\n{details}")
