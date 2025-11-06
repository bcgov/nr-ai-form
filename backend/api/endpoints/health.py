from fastapi import APIRouter
from datetime import datetime
import psutil
import platform
from backend.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "AI Agent API",
    }


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check with system information
    """
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    response = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "AI Agent API",
        "system": {
            "platform": platform.system(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": memory.total,
            "memory_available": memory.available,
            "memory_used": memory.used,
            "memory_used_percent": f"{memory.percent:.1f}%",
            "disk_usage": f"{disk.percent:.1f}%",
        },
    }
    logger.info("Detailed health check performed", response=response)
    return response
