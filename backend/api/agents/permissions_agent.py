import json
import os
import re
from typing import Any, Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# ------------------------------------------------------------------------------
# Logging (stdlib; consistent across agents)
# ------------------------------------------------------------------------------
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
# Heuristics for permissions-related suggestions (patch-compatible)
#   These are intentionally conservative and only emit suggestions when explicit.
#   Field IDs match those used in your orchestrator's mapping example.
# ------------------------------------------------------------------------------
_FEE_EXEMPT_FIELD_IDS = {
    "eligible": "V1IsEligibleForFeeExemption",
    "existing_client": "V1IsExistingExemptClient",
    "client_number": "V1FeeExemptionClientNumber",
    "category": "V1FeeExemptionCategory",
    "supporting": "V1FeeExemptionSupportingInfo",
}

_re_yes_no = re.compile(r"\b(yes|no)\b", re.I)
_re_client_number = re.compile(
    r"\bclient(?:\s*(?:no\.?|number))?\s*[:#]?\s*([A-Za-z0-9\-]+)\b", re.I
)
_re_category = re.compile(r"\bcategory\s*[:\-]\s*([^\n\r;,.]{1,80})", re.I)
_re_supporting = re.compile(
    r"\bsupporting\s*(?:info|information)\s*[:\-]\s*(.{10,400})", re.I
)


def _infer_permissions_suggestions(query: str) -> List[Dict[str, Any]]:
    """
    Inspect the natural-language query and emit zero or more patch-like suggestions:
      { fieldId, value, confidence, rationale }
    Only triggers on very explicit phrases to avoid bad autofill.
    """
    text = (query or "").strip()
    if not text:
        return []

    suggestions: List[Dict[str, Any]] = []
    lowered = text.lower()

    def add_suggestion(
        field_key: str, value: str, confidence: float, rationale: str
    ) -> None:
        field_id = _FEE_EXEMPT_FIELD_IDS.get(field_key)
        if not field_id:
            return
        suggestions.append(
            {
                "fieldId": field_id,
                "value": value,
                "confidence": confidence,
                "rationale": rationale,
                "agent": "PermissionsAgent",
            }
        )

    # 1) Fee exemption yes/no (e.g., "Requesting fee exemption yes")
    if "fee exemption" in lowered or "fee exempt" in lowered:
        m = _re_yes_no.search(lowered)
        if m:
            yn = m.group(1).lower()
            add_suggestion(
                "eligible",
                "Yes" if yn == "yes" else "No",
                0.85,
                "Detected explicit yes/no regarding fee exemption.",
            )

    # 2) Existing exempt client yes/no
    if "existing exempt client" in lowered or "existing exemption client" in lowered:
        m = _re_yes_no.search(lowered)
        if m:
            yn = m.group(1).lower()
            add_suggestion(
                "existing_client",
                "Yes" if yn == "yes" else "No",
                0.8,
                "Detected explicit yes/no for existing exempt client status.",
            )

    # 3) Client number
    m_client = _re_client_number.search(text)
    if m_client:
        add_suggestion(
            "client_number",
            m_client.group(1),
            0.9,
            "Detected an explicit client number in the text.",
        )

    # 4) Exemption category
    m_cat = _re_category.search(text)
    if m_cat:
        value = m_cat.group(1).strip().rstrip(" .;,:")
        if value:
            add_suggestion(
                "category",
                value,
                0.75,
                "Detected an explicit category assignment.",
            )

    # 5) Supporting info
    m_sup = _re_supporting.search(text)
    if m_sup:
        info = m_sup.group(1).strip()
        add_suggestion(
            "supporting",
            info,
            0.7,
            "Detected explicit supporting information segment.",
        )

    return suggestions


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
        select = ["id", "title", "url", "content"]

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
        logger.exception("PermissionsAgent search failed: %s", e)
        return []


# ------------------------------------------------------------------------------
# Public API expected by the orchestrator
#   - permissions_agent(query) -> JSON string (tool-safe)
#   - invoke_permissions_agent(query) -> dict (async-friendly structured)
# Schema mirrors other agents: {agent, query, documents, message}
# Adds optional: "suggestions": [patch-like objects]
# ------------------------------------------------------------------------------
def permissions_agent(query: str, *_args, **_kwargs) -> str:
    """
    Tool-safe entrypoint: accepts a single string and returns a JSON string.
    Payload schema:
      {
        "agent": "PermissionsAgent",
        "query": "<query>",
        "documents": [ {id,title,url,snippet?,content?,score?}, ... ],
        "suggestions": [ {fieldId,value,confidence,rationale,agent?}, ... ],
        "message": "<empty or explanation>"
      }
    """
    docs = _search(query, top=3)
    suggestions = _infer_permissions_suggestions(query)
    payload = {
        "agent": "PermissionsAgent",
        "query": query,
        "documents": docs,
        "suggestions": suggestions,  # optional, patch-compatible for "enter in form"
        "message": "" if (docs or suggestions) else "No compliance guidance found.",
    }
    return json.dumps(payload, default=str)


async def invoke_permissions_agent(query: str, *_args, **_kwargs) -> Dict[str, Any]:
    """
    Async-friendly wrapper that returns a dict (not a formatted string),
    in the same schema used by `permissions_agent`.
    """
    docs = _search(query, top=3)
    suggestions = _infer_permissions_suggestions(query)
    return {
        "agent": "PermissionsAgent",
        "query": query,
        "documents": docs,
        "suggestions": suggestions,
        "message": "" if (docs or suggestions) else "No compliance guidance found.",
    }
