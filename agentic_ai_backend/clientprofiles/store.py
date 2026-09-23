"""Read-only store interface for tenant profile resolution.

This module defines the abstract ClientProfileStore base class — the single
interface through which the orchestrator resolves a tenant's ClientProfile
document. The interface exposes only read methods (get_by_client_id, resolve).

This interface is read-only.
Every request must provide an explicit client_id. Missing or empty client_id
raises ClientIdRequiredError.
"""

import logging
from abc import ABC, abstractmethod

from .exceptions import ClientIdRequiredError, ClientProfileNotFoundError
from .models import ClientProfile

logger = logging.getLogger(__name__)


class ClientProfileStore(ABC):
    """Abstract base class for tenant client profile resolution.

    Subclasses must implement the abstract get_by_client_id method that performs
    the storage-specific read. The resolve() method lives on this base
    class so that all store implementations share identical resolution semantics.
    """

    @abstractmethod
    async def get_by_client_id(self, client_id: str) -> ClientProfile | None:
        """Retrieve a client profile by its unique client_id.

        Args:
            client_id: The GUID identifying the tenant profile to look up.

        Returns:
            The matching ClientProfile, or None if no document with that
            client_id exists in the store.
        """
        ...

    async def resolve(self, client_id: str | None) -> ClientProfile:
        """Resolve a client profile by client_id.

        This method lives on the base class so that
        all implementations share identical resolution semantics. The outcomes:

        1. client_id is non-empty and a matching profile is found → return it.
        2. client_id is non-empty but no matching profile exists → raise
           ClientProfileNotFoundError with the unmatched value.
        3. client_id is None or empty → raise ClientIdRequiredError.

        Args:
            client_id: The tenant identifier from the request body.

        Returns:
            The resolved ClientProfile.

        Raises:
            ClientIdRequiredError: When client_id is None, empty, or
                whitespace-only.
            ClientProfileNotFoundError: When a non-empty client_id has no
                matching profile in the store.
        """
        # Whitespace-strip normalisation: treat empty string and whitespace-only
        # strings the same as None — all are considered "missing".
        normalised_id = client_id.strip() if client_id else None

        if not normalised_id:
            # client_id is required — no default profile exists.
            logger.warning("resolve: client_id is missing or empty")
            raise ClientIdRequiredError()

        logger.debug(
            "resolve: client_id=%s strategy=by_client_id", normalised_id
        )
        profile = await self.get_by_client_id(normalised_id)
        if profile is not None:
            return profile

        logger.warning("resolve: client_id=%s not found", normalised_id)
        raise ClientProfileNotFoundError(normalised_id)
