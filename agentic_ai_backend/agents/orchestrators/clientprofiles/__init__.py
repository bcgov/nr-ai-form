"""Cosmos DB multitenancy client profiles package.

Provides Pydantic data models and store abstractions for resolving per-tenant
configuration from Azure Cosmos DB. Each tenant's ClientProfile document
defines its sub-agents, prompt paths, tenant resources, and CORS origins.

Every request must provide an explicit client_id.
"""

from .cosmos_store import CosmosClientProfileStore
from .exceptions import ClientIdRequiredError, ClientProfileNotFoundError
from .factory import get_client_profile_store
from .models import (
    ClientProfile,
    OrchestratorPrompts,
    SubAgentConfig,
    TenantResources,
)
from .store import ClientProfileStore

__all__ = [
    "ClientIdRequiredError",
    "ClientProfile",
    "ClientProfileNotFoundError",
    "ClientProfileStore",
    "CosmosClientProfileStore",
    "OrchestratorPrompts",
    "SubAgentConfig",
    "TenantResources",
    "get_client_profile_store",
]
