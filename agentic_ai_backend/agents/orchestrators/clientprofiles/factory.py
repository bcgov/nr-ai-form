"""Factory for the ClientProfileStore singleton.

Provides a single entry point — get_client_profile_store() — that lazily creates
and caches a CosmosClientProfileStore instance. The singleton is shared across all
requests within the same process, ensuring at-most-once Cosmos DB client
initialisation and connection establishment.

Credential resolution follows a fixed priority chain:
  1. AZURE_COSMOS_DB_KEY (account key + endpoint) — local emulator & non-MI envs
  2. DefaultAzureCredential (any Azure-hosted env with Managed Identity: dev, test, prod)

TLS certificate verification is disabled when CSSAI_EXECUTION_ENV=localhost,
allowing the Cosmos emulator's self-signed certificate to be accepted.
"""

import os

from .cosmos_store import CosmosClientProfileStore
from .store import ClientProfileStore

# Module-level singleton — initialised at most once on the first call to
# get_client_profile_store(). Subsequent calls return this cached instance
# without re-connecting to Cosmos DB.
_store_instance: ClientProfileStore | None = None


def get_client_profile_store() -> ClientProfileStore:
    """Return the shared ClientProfileStore singleton.

    Creates a CosmosClientProfileStore on the first call, using environment
    variables for credential and endpoint configuration. All subsequent calls
    return the same instance.

    Returns:
        The singleton ClientProfileStore (always a CosmosClientProfileStore).
    """
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    endpoint = os.getenv("AZURE_COSMOS_DB_ENDPOINT")
    database_name = os.getenv("AZURE_COSMOS_DB_DATABASE_NAME", "AgentMemoryDB")
    container_name = "ClientProfiles"

    key = os.getenv("AZURE_COSMOS_DB_KEY")
    disable_ssl = os.getenv("CSSAI_EXECUTION_ENV", "").lower() == "localhost"

    # The factory always creates a CosmosClientProfileStore regardless of
    # environment. Both local development (Cosmos emulator) and production
    # (Azure Cosmos DB) use the same store; only the credentials and TLS
    # settings differ.
    _store_instance = CosmosClientProfileStore(
        endpoint=endpoint,
        database_name=database_name,
        container_name=container_name,
        key=key,
        disable_ssl=disable_ssl,
    )
    return _store_instance
