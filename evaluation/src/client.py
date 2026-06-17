"""Backend API client."""

import logging
import json
import httpx
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
from pathlib import Path

from src.config import settings

logger = logging.getLogger(__name__)
INVOKE_PATH = "/invoke"


class BackendClient:
    """Client for backend API."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        raw_url = (base_url or settings.backend_api_url).rstrip("/")
        parsed = urlparse(raw_url)
        self.invoke_path = INVOKE_PATH
        self.base_url = raw_url.replace(INVOKE_PATH, "") if parsed.path.endswith(INVOKE_PATH) else raw_url
        self.timeout = timeout or settings.backend_api_timeout
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def health_check(self) -> bool:
        """Check backend health."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            logger.exception("health_check_failed")
            return False

    async def invoke(self, *, query: str, step_number: Optional[str] = None) -> Dict[str, Any]:
        """Call backend invoke endpoint."""
        payload = {"query": query}
        if step_number:
            payload["step_number"] = step_number
        try:
            #import pdb; pdb.set_trace()
            resp = await self.client.post(self.invoke_path, json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.exception("invoke_failed")
            raise

    def get_sample_cases(self) -> List[Dict[str, Any]]:
        """Load test cases from JSON file."""
        try:
            file = Path(__file__).parent / "../data/test_cases.json"
            if not file.exists():
                logger.warning("test_cases_not_found")
                return []
            data = json.load(open(file))
            cases = data.get("test_cases", [])
            logger.info("cases_loaded", count=len(cases))
            return cases
        except Exception:
            logger.exception("load_test_cases_failed")
            return []

    async def close(self):
        """Close client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

