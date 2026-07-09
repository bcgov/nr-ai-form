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
    ConversationAgentConfig,
    FormSupportAgentConfig,
    OrchestratorPrompts,
    OrchestratorRuntimeSettings,
    SubAgentConfig,
    TenantResources,
)
from .store import ClientProfileStore
from .settings import (
    ConversationAgentSettings,
    FormSupportAgentSettings,
    OrchestratorPromptSettings,
    TenantAgentSettings,
    TenantSettingsValidationError,
    build_config_fingerprint,
    build_tenant_agent_settings,
    validate_client_profiles,
)
from .tenant_config import (
    TenantConfig,
    TenantConfigInvalidError,
    TenantConfigService,
    TenantConfigUnavailableError,
    is_origin_allowed,
)

__all__ = [
    "ClientIdRequiredError",
    "ClientProfile",
    "ClientProfileNotFoundError",
    "ClientProfileStore",
    "ConversationAgentConfig",
    "CosmosClientProfileStore",
    "FormSupportAgentConfig",
    "OrchestratorPrompts",
    "OrchestratorRuntimeSettings",
    "SubAgentConfig",
    "TenantConfig",
    "TenantConfigInvalidError",
    "TenantConfigService",
    "TenantConfigUnavailableError",
    "TenantResources",
    "get_client_profile_store",
    "ConversationAgentSettings",
    "FormSupportAgentSettings",
    "OrchestratorPromptSettings",
    "TenantAgentSettings",
    "TenantSettingsValidationError",
    "build_config_fingerprint",
    "build_tenant_agent_settings",
    "validate_client_profiles",
    "is_origin_allowed",
]
