"""Cached tenant profile lookup, typed settings, and origin validation helpers."""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from pydantic import ValidationError

from .exceptions import ClientIdRequiredError, ClientProfileNotFoundError
from .models import ClientProfile
from .settings import (
    TenantAgentSettings,
    TenantSettingsValidationError,
    build_tenant_agent_settings,
)
from .store import ClientProfileStore

logger = logging.getLogger(__name__)


class TenantConfigUnavailableError(Exception):
    """Raised when a tenant profile cannot be loaded and no stale cache exists."""


class TenantConfigInvalidError(ValueError):
    """Raised when a tenant profile is present but not usable by runtime agents."""


@dataclass(frozen=True)
class TenantConfig:
    """Validated runtime tenant configuration cached at the gateway boundary."""

    profile: ClientProfile
    settings: TenantAgentSettings
    fingerprint: str


@dataclass
class _CachedTenantConfig:
    config: TenantConfig
    fresh_until: float
    stale_until: float


@dataclass
class _CachedClientProfile:
    profile: ClientProfile
    fresh_until: float
    stale_until: float


class TenantConfigService:
    """Resolve tenant config with fresh/stale cache fallback.

    WebSocket handshakes need tenant config before `accept()`. A short Cosmos
    timeout prevents handshakes from hanging, while stale cache lets known tenants
    continue through a temporary Cosmos outage. Unknown tenants still fail closed.
    """

    def __init__(
        self,
        store: ClientProfileStore,
        fresh_ttl_seconds: float | None = None,
        stale_ttl_seconds: float | None = None,
        lookup_timeout_seconds: float | None = None,
    ) -> None:
        self._store = store
        self._cache: dict[str, _CachedTenantConfig] = {}
        self._profile_cache: dict[str, _CachedClientProfile] = {}
        self._fresh_ttl = (
            fresh_ttl_seconds
            if fresh_ttl_seconds is not None
            else float(os.getenv("TENANT_PROFILE_FRESH_TTL_SECONDS", "300"))
        )
        self._stale_ttl = (
            stale_ttl_seconds
            if stale_ttl_seconds is not None
            else float(os.getenv("TENANT_PROFILE_STALE_TTL_SECONDS", "86400"))
        )
        self._lookup_timeout = (
            lookup_timeout_seconds
            if lookup_timeout_seconds is not None
            else float(os.getenv("TENANT_PROFILE_LOOKUP_TIMEOUT_SECONDS", "0.5"))
        )

    async def get_config(self, client_id: str | None) -> TenantConfig:
        normalised_id = client_id.strip() if client_id else None
        if not normalised_id:
            raise ClientIdRequiredError()

        now = time.monotonic()
        cached = self._cache.get(normalised_id)
        if cached and self._fresh_ttl > 0 and now < cached.fresh_until:
            return cached.config

        try:
            profile = await self.get_profile(normalised_id)
            settings = build_tenant_agent_settings(profile)
        except (ClientIdRequiredError, ClientProfileNotFoundError):
            # A known invalid tenant must not be rescued by stale cache.
            self._cache.pop(normalised_id, None)
            raise
        except (TenantSettingsValidationError, ValidationError) as exc:
            self._cache.pop(normalised_id, None)
            raise TenantConfigInvalidError(str(exc)) from exc
        except Exception as exc:
            if cached and self._stale_ttl > 0 and now < cached.stale_until:
                logger.warning(
                    "Using stale tenant config after lookup failure",
                    extra={"client_id": normalised_id, "error_type": type(exc).__name__},
                )
                return cached.config
            raise TenantConfigUnavailableError(
                f"Tenant config unavailable for client_id: {normalised_id}"
            ) from exc

        config = TenantConfig(
            profile=profile,
            settings=settings,
            fingerprint=settings.config_fingerprint,
        )
        if self._fresh_ttl > 0 or self._stale_ttl > 0:
            self._cache[normalised_id] = _CachedTenantConfig(
                config=config,
                fresh_until=now + self._fresh_ttl,
                stale_until=now + self._stale_ttl,
            )
        return config

    async def get_profile(self, client_id: str | None) -> ClientProfile:
        """Resolve only the raw tenant profile for lightweight boundary checks.

        CORS and WebSocket origin checks need the tenant allow-list before route
        handling, but they should not validate every downstream agent setting.
        Full typed settings are validated by get_config() when a request is
        actually invoked.
        """
        normalised_id = client_id.strip() if client_id else None
        if not normalised_id:
            raise ClientIdRequiredError()

        now = time.monotonic()
        cached = self._profile_cache.get(normalised_id)
        if cached and self._fresh_ttl > 0 and now < cached.fresh_until:
            return cached.profile

        try:
            profile = await asyncio.wait_for(
                self._store.resolve(normalised_id),
                timeout=self._lookup_timeout,
            )
        except (ClientIdRequiredError, ClientProfileNotFoundError):
            self._cache.pop(normalised_id, None)
            self._profile_cache.pop(normalised_id, None)
            raise
        except Exception as exc:
            logger.warning(
                "Tenant profile lookup failed",
                extra={"client_id": normalised_id, "error_type": type(exc).__name__},
            )
            if cached and self._stale_ttl > 0 and now < cached.stale_until:
                logger.warning(
                    "Using stale tenant profile after lookup failure",
                    extra={"client_id": normalised_id, "error_type": type(exc).__name__},
                )
                return cached.profile
            raise TenantConfigUnavailableError(
                f"Tenant profile unavailable for client_id: {normalised_id}"
            ) from exc

        if self._fresh_ttl > 0 or self._stale_ttl > 0:
            self._profile_cache[normalised_id] = _CachedClientProfile(
                profile=profile,
                fresh_until=now + self._fresh_ttl,
                stale_until=now + self._stale_ttl,
            )
        return profile

    async def get_settings(self, client_id: str | None) -> TenantAgentSettings:
        return (await self.get_config(client_id)).settings


def _normalise_origin(value: str | None) -> str | None:
    if not value:
        return None

    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}".rstrip("/")


def _normalise_allowed_origin(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = value.strip()
    # Origins never include paths. Existing seed data may end in /*, so strip it.
    cleaned = cleaned.removesuffix("/*").rstrip("/")
    return _normalise_origin(cleaned)


def _is_localhost_wildcard_allowed(normalised_origin: str, allowed: str) -> bool:
    """Allow dev-only patterns such as http://localhost* without matching lookalike hosts."""
    cleaned = allowed.strip().removesuffix("/*").rstrip("/")
    if not cleaned.endswith("*"):
        return False

    base = cleaned[:-1]
    parsed_base = urlparse(base)
    parsed_origin = urlparse(normalised_origin)
    if parsed_base.scheme not in {"http", "https"}:
        return False

    localhost_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed_base.hostname not in localhost_hosts:
        return False

    return (
        parsed_origin.scheme == parsed_base.scheme.lower()
        and parsed_origin.hostname in localhost_hosts
    )


def is_origin_allowed(origin: str | None, allowed_origins: list[str]) -> bool:
    """Return True when the request Origin matches the tenant allow-list.

    Production tenant profiles should use exact origins. The only wildcard form
    accepted here is localhost-style local development, e.g. ``http://localhost*``.
    """

    normalised_origin = _normalise_origin(origin)
    if not normalised_origin:
        return False

    for allowed in allowed_origins or []:
        pattern = _normalise_allowed_origin(allowed)
        if pattern and normalised_origin == pattern:
            return True
        if _is_localhost_wildcard_allowed(normalised_origin, allowed):
            return True

    return False
