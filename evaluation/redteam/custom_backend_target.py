"""PyRIT target using the same transport as Promptfoo and DeepEval."""

from __future__ import annotations

import uuid

import httpx
import structlog
from pyrit.models import Message
from pyrit.prompt_target import PromptTarget
from pyrit.prompt_target.common.target_capabilities import TargetCapabilities
from pyrit.prompt_target.common.target_configuration import TargetConfiguration

from shared.backend_client import BackendClient, BackendError, extract_text

logger = structlog.get_logger(__name__)
INFRA_ERROR_PREFIX = "INFRA_ERROR::"


class CustomBackendTarget(PromptTarget):
    _DEFAULT_CONFIGURATION = TargetConfiguration(
        capabilities=TargetCapabilities(
            supports_multi_turn=True,
            supports_editable_history=True,
            supports_system_prompt=False,
        )
    )

    def __init__(
        self,
        *,
        endpoint: str,
        session_id: str | None = None,
        step_number: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._client = BackendClient(endpoint, timeout, session_id)
        super().__init__()
        self.endpoint = endpoint
        self.step_number = step_number
        self.timeout = timeout
        self._conversation_id = str(uuid.uuid4())
        self._clients: dict[str, BackendClient] = {}
        self._histories: dict[str, list[tuple[str, str]]] = {}

    async def _send_prompt_to_target_async(
        self, *, normalized_conversation: list[Message]
    ) -> list[Message]:
        last_message = next(
            (message for message in reversed(normalized_conversation) if message.api_role == "user"),
            None,
        )
        if last_message is None:
            logger.error("backend_no_user_message")
            return [Message.from_prompt(
                prompt=f"{INFRA_ERROR_PREFIX}NO_USER_MESSAGE::No user message in conversation",
                role="assistant",
            )]
        conversation_id = str(last_message.conversation_id)
        if conversation_id not in self._clients:
            # Seed objectives can run concurrently: each needs its own backend session.
            self._clients[conversation_id] = (
                BackendClient(self.endpoint, self.timeout) if self._clients else self._client
            )
        client = self._clients[conversation_id]
        history = [
            (message.api_role, str(message.get_value()))
            for message in normalized_conversation
            if message.api_role in {"user", "assistant"}
        ]
        prefix = history[:-1]
        try:
            if prefix != self._histories.get(conversation_id, []):
                # Crescendo forks or edits history when backtracking. Reset the remote
                # session and replay retained user turns; the backend regenerates replies.
                await client.close()
                client = self._clients[conversation_id] = BackendClient(self.endpoint, self.timeout)
                for role, text in prefix:
                    if role == "user":
                        await client.invoke(text, self.step_number)
            response = await client.invoke(str(last_message.get_value()), self.step_number)
            text = extract_text(response["response"])
            self._histories[conversation_id] = history + [("assistant", text)]
        except (BackendError, httpx.HTTPError, ValueError) as exc:
            logger.error("backend_request_failed", error=str(exc))
            self._histories.pop(conversation_id, None)
            text = f"{INFRA_ERROR_PREFIX}BACKEND_REQUEST::{exc}"
        return [Message.from_prompt(prompt=text, role="assistant")]

    @property
    def supported_chat_message_roles(self) -> list[str]:
        return ["user", "assistant"]

    def _get_identifier(self) -> str:
        return f"CustomBackendTarget::{self._conversation_id}"

    async def close_async(self) -> None:
        await self._client.close()
        for client in self._clients.values():
            await client.close()
