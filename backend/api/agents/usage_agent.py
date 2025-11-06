from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from backend.core.logging import get_logger

logger = get_logger(__name__)


# ------------------------------------------------------------------------------
# Azure Cognitive Search (READS use the QUERY key; keep vars consistent)
# ------------------------------------------------------------------------------
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_INDEX = os.getenv(
    "AZURE_SEARCH_INDEX_NAME", "bc-water-index"
)  # single source of truth across repo
SEARCH_QUERY_KEY = os.getenv("AZURE_SEARCH_KEY")


_search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=SEARCH_INDEX,
    credential=AzureKeyCredential(SEARCH_QUERY_KEY),
)


# ------------------------------------------------------------------------------
# Internal search helper (compact projection + optional snippet)
# ------------------------------------------------------------------------------
def _search(
    query: str,
    *,
    top: int = 3,
    select: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Query the index and return a compact list of dicts suitable for downstream use.
    """
    if not select:
        # Keep projection tight; adjust fields to your index schema.
        select = ["*", "title", "url", "content"]

    try:
        results = _search_client.search(search_text=query, select=["*"], top=top)
        docs: List[Dict[str, Any]] = []
        for r in results:
            doc = {k: r.get(k) for k in select if k in r}
            score = r.get("@search.score")
            if score is not None:
                doc["score"] = score
            # Provide a short snippet if content is long (non-destructive).
            content = doc.get("content")
            if isinstance(content, str) and len(content) > 400:
                doc["snippet"] = content[:400] + "…"
            docs.append(doc)
        return docs
    except Exception as e:
        logger.exception("UsageAgent search failed: %s", e)
        return []


# ------------------------------------------------------------------------------
# Public API expected by the orchestrator
#   - usage_agent(query) -> JSON string (tool-safe)
#   - invoke_usage_agent(query) -> dict (async-friendly structured)
# Schema mirrors source_agent: {agent, query, documents, message}
# ------------------------------------------------------------------------------
def usage_agent(query: str, *_args, **_kwargs) -> str:
    """
    Tool-safe entrypoint: accepts a single string and returns a JSON string.
    Payload schema:
      {
        "agent": "UsageAgent",
        "query": "<query>",
        "documents": [ {id,title,url,snippet?,content?,score?}, ... ],
        "message": "<empty or explanation>"
      }
    """
    docs = _search(query, top=3)
    payload = {
        "agent": "UsageAgent",
        "query": query,
        "documents": docs,
        "message": "" if docs else "No relevant data found for usage query.",
    }
    return json.dumps(payload, default=str)


async def invoke_usage_agent(query: str, *_args, **_kwargs) -> Dict[str, Any]:
    """
    Async-friendly wrapper that returns a dict (not a formatted string),
    in the same schema used by `usage_agent`.
    """
    # The underlying Azure SDK call is synchronous; call directly.
    docs = _search(query, top=3)
    return {
        "agent": "UsageAgent",
        "query": query,
        "documents": docs,
        "message": "" if docs else "No relevant data found for usage query.",
    }
