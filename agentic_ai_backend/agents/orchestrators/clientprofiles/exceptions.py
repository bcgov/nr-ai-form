"""Domain-specific exceptions for the client profiles multitenancy layer."""


class ClientIdRequiredError(Exception):
    """Raised when resolve() is called without a client_id.

    Every request must include a valid client_id to identify the tenant.
    There is no default profile — callers must always provide an explicit
    client_id in the request body.
    """

    def __init__(self) -> None:
        super().__init__(
            "client_id is required. Please provide a valid client_id "
            "in the request body to identify your tenant."
        )


class ClientProfileNotFoundError(Exception):
    """Raised when resolve() is given a non-empty client_id that does not
    match any document in the ClientProfiles Cosmos DB container.

    This is a domain-specific error indicating the caller provided a client_id
    (i.e. the value is non-empty after whitespace stripping) but no
    corresponding ClientProfile document exists in the store.
    """

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        super().__init__(
            f"No client profile found for client_id: '{client_id}'. "
            f"Please verify the client_id is correct and has been provisioned."
        )
