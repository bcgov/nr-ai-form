"""Process-local tenant config service for orchestrator routes and middleware."""

from clientprofiles import TenantConfigService, get_client_profile_store

_tenant_config_service: TenantConfigService | None = None


def get_tenant_config_service() -> TenantConfigService:
    """Return the shared tenant config cache for this orchestrator process."""
    global _tenant_config_service
    if _tenant_config_service is None:
        _tenant_config_service = TenantConfigService(get_client_profile_store())
    return _tenant_config_service