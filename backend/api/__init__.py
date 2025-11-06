from fastapi import APIRouter
from backend.api.endpoints import health
from backend.api.endpoints import indexer, orchestrator_endpoints

# Create main API router
router = APIRouter()

# Include endpoint routers
router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(indexer.router, prefix="/indexer", tags=["indexer"])
router.include_router(
    orchestrator_endpoints.router, prefix="/orchestrator", tags=["orchestrator"]
)
