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
# Internal helper
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
        # keep projection tight; adjust to your index schema
        select = ["id", "title", "url", "content"]

    try:
        results = _search_client.search(search_text=query, select=["*"], top=top)
        docs: List[Dict[str, Any]] = []
        for r in results:
            # `r` behaves like a dict; include score if present
            doc = {k: r.get(k) for k in select if k in r}
            score = r.get("@search.score")
            if score is not None:
                doc["score"] = score
            # provide a short snippet if content is long
            content = doc.get("content")
            if isinstance(content, str) and len(content) > 400:
                doc["snippet"] = content[:400] + "…"
            docs.append(doc)
        return docs
    except Exception as e:
        logger.exception("SourceAgent search failed: %s", e)
        return []


# ------------------------------------------------------------------------------
# Public API expected by the orchestrator
#   - source_agent(query) -> JSON string (for LangChain Tool safety)
#   - invoke_source_agent(query) -> dict (async-friendly wrapper)
# ------------------------------------------------------------------------------
def source_agent(query: str, *_args, **_kwargs) -> str:
    """
    Tool-safe entrypoint: accepts a single string and returns a JSON string.
    Payload schema:
      {
        "agent": "SourceAgent",
        "query": "<query>",
        "documents": [ {id,title,url,snippet?,content?,score?}, ... ],
        "message": "<empty or explanation>"
      }
    """
    docs = _search(query, top=3)
    payload = {
        "agent": "SourceAgent",
        "query": query,
        "documents": docs,
        "message": "" if docs else "No relevant data found for source query.",
    }
    return json.dumps(payload, default=str)


async def invoke_source_agent(query: str, *_args, **_kwargs) -> Dict[str, Any]:
    """
    Async-friendly wrapper that returns a dict (not a formatted string),
    in the same schema used by `source_agent`.
    """
    # The underlying Azure SDK call is synchronous; we simply call it in-place.
    docs = _search(query, top=3)
    return {
        "agent": "SourceAgent",
        "query": query,
        "documents": docs,
        "message": "" if docs else "No relevant data found for source query.",
    }
