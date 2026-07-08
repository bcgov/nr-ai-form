"""Multitenancy data models for the Cosmos DB client profile layer.

This module defines the Pydantic models that represent per-tenant configuration
documents stored in Azure Cosmos DB. Each tenant (client application) has a
ClientProfile document that describes its sub-agents, prompt paths, tenant
resources, and CORS origins. These models provide typed, validated access to
the document fields while tolerating the extra metadata fields that Cosmos DB
adds to every document.
"""

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _is_missing(value: Any) -> bool:
    return value in (None, "")


class ConversationAgentConfig(BaseModel):
    """Known conversation-agent config keys; extra keys are preserved for rollout safety."""

    model_config = ConfigDict(extra="allow")

    conversationAgentMode: Literal["knowledgebase", "llm"] | None = None
    azureSearchEndpoint: str | None = None
    azureSearchApiKey: str | None = None
    azureSearchIndexName: str | None = None
    azureSearchKnowledgeAgentName: str | None = None
    azureSearchKnowledgeAgentApiVersion: str | None = None
    azureSearchKnowledgeAgentRequestMode: Literal["messages", "intents"] | None = None
    azureSearchKnowledgeAgentOutputMode: Literal["answerSynthesis", "extractiveData"] | None = None
    azureSearchKnowledgeAgentReasoningEffort: Literal["minimal", "low", "medium"] | None = None
    azureSearchKnowledgeAgentMaxOutputSize: int | None = None
    azureSearchKnowledgeAgentMaxRuntimeSeconds: int | None = None
    azureSearchKnowledgeAgentMaxHistoryMessages: int | None = None
    azureSearchTop: int | None = None
    azureSearchTrimLength: int | None = None
    azureSearchEnableTrimming: bool | None = None
    azureSearchIncludeTotalCount: bool | None = None
    azureSearchQueryType: str | None = None
    azureSearchSemanticConfiguration: str | None = None
    azureSearchQueryCaption: str | None = None
    azureSearchQueryAnswer: str | None = None
    azureSearchQueryAnswerCount: int | None = None
    azureSearchQueryLanguage: str | None = None
    azureOpenaiEndpoint: str | None = None
    azureOpenaiApiKey: str | None = None
    azureOpenaiChatDeploymentName: str | None = None
    azureOpenaiApiVersion: str | None = None
    agentMaxTokens: int | None = None
    agentTemperature: float | None = None


class FormSupportAgentConfig(BaseModel):
    """Known form-support config keys; extra keys are preserved for rollout safety."""

    model_config = ConfigDict(extra="allow")

    formDefinitionContainer: str | None = None
    stepBasedPromptContainer: str | None = None
    azureOpenaiEndpoint: str | None = None
    azureOpenaiApiKey: str | None = None
    azureOpenaiChatDeploymentName: str | None = None
    azureOpenaiApiVersion: str | None = None


class OrchestratorRuntimeSettings(BaseModel):
    """Tenant-specific orchestrator runtime configuration from tenantResources.config."""

    model_config = ConfigDict(extra="allow")

    azureOpenAIEndpoint: str | None = None
    azureOpenAIChatDeploymentName: str | None = None
    azureOpenAIApiVersion: str | None = None
    azureOpenAIApiKey: str | None = None
    azureOpenAIAggregatorChatDeploymentName: str | None = None
    azureOpenAIAggregatorMaxCompletionTokens: int | None = None
    formStepNumber: str | None = None
    a2aClientTimeoutSeconds: int | None = None

    @field_validator("azureOpenAIAggregatorMaxCompletionTokens", "a2aClientTimeoutSeconds", mode="before")
    @classmethod
    def _parse_optional_int(cls, value: Any) -> int | None:
        if _is_missing(value):
            return None
        return int(value)

    @field_validator("formStepNumber", mode="before")
    @classmethod
    def _parse_optional_step(cls, value: Any) -> str | None:
        if _is_missing(value):
            return None
        return str(value)


class OrchestratorPrompts(BaseModel):
    """Paths to orchestrator-level prompt templates in blob storage."""

    dispatcher: str
    aggregator: str


class TenantResources(BaseModel):
    """Shared storage and orchestrator-level prompt configuration for a tenant.

    Contains the Azure Blob connection details and prompt paths needed by the
    orchestrator to load tenant-specific dispatcher and aggregator prompts.
    """

    # TODO: Replace raw secret fields with Key Vault references or managed identity
    # where supported. Cosmos tenant profiles should store references/non-secret
    # config, and the tenant settings boundary should resolve secrets before use.
    blobConnectionString: str
    containerName: str
    prompts: OrchestratorPrompts
    config: OrchestratorRuntimeSettings = Field(default_factory=OrchestratorRuntimeSettings)


class SubAgentConfig(BaseModel):
    """Configuration for a supported sub-agent within a tenant profile."""

    agentType: Literal["conversationAgent", "formSupportAgent"]
    enabled: bool = True
    promptPath: Optional[str] = None
    config: ConversationAgentConfig | FormSupportAgentConfig = Field(default_factory=ConversationAgentConfig)

    @model_validator(mode="before")
    @classmethod
    def _coerce_config_for_agent_type(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        agent_type = data.get("agentType")
        raw_config = data.get("config") or {}
        if agent_type == "conversationAgent":
            data = {**data, "config": ConversationAgentConfig.model_validate(raw_config)}
        elif agent_type == "formSupportAgent":
            data = {**data, "config": FormSupportAgentConfig.model_validate(raw_config)}
        return data


class ClientProfile(BaseModel):
    """A single tenant's configuration document from Azure Cosmos DB.

    Represents the complete profile for one client application, including
    its sub-agent definitions, tenant resources, and allowed CORS origins.
    """

    # Silently drop unknown Cosmos DB system fields (_rid, _self, _etag, _ts,
    # _attachments, id, etc.) that are present on every document but are not
    # part of our domain model. Without this, Pydantic would raise a
    # ValidationError on deserialisation.
    model_config = {"extra": "ignore"}

    # clientId doubles as both the Cosmos DB document `id` and the partition
    # key value, enabling O(1) point reads without cross-partition queries.
    clientId: str
    clientName: str
    corsOrigins: List[str] = Field(default_factory=list)
    tenantResources: Optional[TenantResources] = None
    subAgents: List[SubAgentConfig] = Field(default_factory=list)
