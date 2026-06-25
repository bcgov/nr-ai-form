"""Multitenancy data models for the Cosmos DB client profile layer.

This module defines the Pydantic models that represent per-tenant configuration
documents stored in Azure Cosmos DB. Each tenant (client application) has a
ClientProfile document that describes its sub-agents, prompt paths, tenant
resources, and CORS origins. These models provide typed, validated access to
the document fields while tolerating the extra metadata fields that Cosmos DB
adds to every document.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OrchestratorPrompts(BaseModel):
    """Paths to orchestrator-level prompt templates in blob storage."""

    dispatcher: str
    aggregator: str


class TenantResources(BaseModel):
    """Shared storage and orchestrator-level prompt configuration for a tenant.

    Contains the Azure Blob connection details and prompt paths needed by the
    orchestrator to load tenant-specific dispatcher and aggregator prompts.
    """

    blobConnectionString: str
    containerName: str
    prompts: OrchestratorPrompts


class SubAgentConfig(BaseModel):
    """Configuration for a single sub-agent within a tenant's profile.

    The `config` dictionary is intentionally freeform — it accepts any
    key-value pairs without schema validation so that agent-type-specific
    settings (e.g. RAG/search config for a conversationAgent, form definition
    paths for a formSupportAgent) can vary per agent type without requiring
    model changes.
    """

    agentType: str
    enabled: bool = True
    promptPath: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


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
