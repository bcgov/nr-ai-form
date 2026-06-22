"""Cosmos DB implementation of the ClientProfileStore interface.

This is the store implementation for all environments — both the local
Cosmos emulator (docker-compose, port 8081) and Azure Cosmos DB.
The factory always creates a CosmosClientProfileStore regardless of environment.

The store is read-only: it exposes only the point-read operation
(get_by_client_id) and inherits the resolve() algorithm from the abstract base
class.
There is no default profile — every request must provide an explicit client_id.
"""

import logging

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from .models import ClientProfile
from .store import ClientProfileStore

logger = logging.getLogger(__name__)


class CosmosClientProfileStore(ClientProfileStore):
    """Cosmos DB-backed store for reading tenant ClientProfile documents.

    Uses point reads (read_item).
    Connects using a two-option credential chain:
      1. Endpoint + Key (AZURE_COSMOS_DB_KEY) — for local emulator and environments without Managed Identity.
      2. Endpoint + DefaultAzureCredential — for any Azure-hosted environment (dev, test, prod) with Managed Identity.
    TLS verification is disabled when running against the local Cosmos emulator.
    """

    def __init__(
        self,
        endpoint: str,
        database_name: str,
        container_name: str,
        key: str | None = None,
        disable_ssl: bool = False,
    ) -> None:
        # Credential chain priority order:
        # 1. Account key (AZURE_COSMOS_DB_KEY) — used by the Cosmos emulator
        #    and any environment where Managed Identity is not available.
        # 2. DefaultAzureCredential — used in any Azure-hosted environment (dev, test, prod) with Managed Identity.
        # Only the first available credential is used.
        if key:
            self._client = CosmosClient(
                endpoint,
                credential=key,
                # connection_verify=False disables TLS cert verification.
                # The Cosmos emulator uses a self-signed certificate that fails
                # standard chain-of-trust validation, so TLS verification must
                # be disabled in local development.
                connection_verify=not disable_ssl,
            )
        else:
            from azure.identity import DefaultAzureCredential

            self._client = CosmosClient(
                endpoint,
                credential=DefaultAzureCredential(),
                # connection_verify=False disables TLS cert verification.
                # The Cosmos emulator uses a self-signed certificate that fails
                # standard chain-of-trust validation.
                connection_verify=not disable_ssl,
            )

        db = self._client.get_database_client(database_name)
        self._container = db.get_container_client(container_name)

    async def get_by_client_id(self, client_id: str) -> ClientProfile | None:
        """Retrieve a client profile by its unique client_id using a point read.

        Uses read_item (point read) with client_id as both the document id and
        partition key value.

        Args:
            client_id: The GUID identifying the tenant profile.

        Returns:
            The matching ClientProfile, or None if no document exists.
        """
        try:
            # Point read (read_item).
            # Point reads are O(1) lookups by partition key + document id,
            # costing exactly 1 RU regardless of document size.
            doc = self._container.read_item(
                item=client_id, partition_key=client_id
            )
            return ClientProfile.model_validate(doc)
        except CosmosResourceNotFoundError:
            return None
