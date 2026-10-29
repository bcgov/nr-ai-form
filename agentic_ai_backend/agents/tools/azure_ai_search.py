import hashlib
import inspect
import json
import logging
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.search.documents import SearchClient

from agent_framework import tool
from utils.tenantsettings import AZURE_SEARCH_API_KEY_ENV, AZURE_SEARCH_ENDPOINT_ENV, environment_setting, setting_from_client_config

logger = logging.getLogger(__name__)


def _parse_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).lower() == "true"


def _search_settings(client_settings: dict) -> dict:
    """Effective search settings for a tenant, with code defaults applied."""
    return {
        "index_name": setting_from_client_config(client_settings, "azureSearchIndexName", required=True),
        "top": int(setting_from_client_config(client_settings, "azureSearchTop", default=3)),
        "trim_length": int(setting_from_client_config(client_settings, "azureSearchTrimLength", default=500)),
        "enable_trimming": _parse_bool(setting_from_client_config(client_settings, "azureSearchEnableTrimming", default="true"), True),
        "include_total_count": _parse_bool(setting_from_client_config(client_settings, "azureSearchIncludeTotalCount", default="true"), True),
        "query_type": setting_from_client_config(client_settings, "azureSearchQueryType", default="semantic"),
        "semantic_configuration": setting_from_client_config(client_settings, "azureSearchSemanticConfiguration", default="semanticconfig"),
        "query_caption": setting_from_client_config(client_settings, "azureSearchQueryCaption", default="extractive"),
        "query_answer": setting_from_client_config(client_settings, "azureSearchQueryAnswer", default="extractive"),
        "query_answer_count": int(setting_from_client_config(client_settings, "azureSearchQueryAnswerCount", default=3)),
        "query_language": setting_from_client_config(client_settings, "azureSearchQueryLanguage", default="en-us"),
        # Variance experiment flags - all default off.
        "deterministic_order": _parse_bool(setting_from_client_config(client_settings, "azureSearchDeterministicOrder", default=False), False),
        "scoring_statistics_global": _parse_bool(setting_from_client_config(client_settings, "azureSearchScoringStatisticsGlobal", default=False), False),
        "use_session_id": _parse_bool(setting_from_client_config(client_settings, "azureSearchUseSessionId", default=False), False),
    }


def search_config_version(client_settings: dict) -> str:
    """Short hash of the effective search settings, so runs can be compared per config."""
    payload = json.dumps(_search_settings(client_settings), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def search_documents(query: str, client_settings: dict, session_id: str | None = None) -> tuple[list[dict], list[str], int | None, dict]:
    """Run one Azure AI Search request.

    Returns (documents, semantic_answers, total_count, retrieval). Documents are plain
    dicts in service order. Service errors are reported in retrieval["error"] rather
    than raised; missing configuration still raises ValueError.
    """
    endpoint = environment_setting(AZURE_SEARCH_ENDPOINT_ENV, required=True)
    key = environment_setting(AZURE_SEARCH_API_KEY_ENV, required=True)
    settings = _search_settings(client_settings)

    if not endpoint or not key or not settings["index_name"]:
        raise ValueError("Azure AI Search is not configured: endpoint, api key, and index name are required.")

    query = query.strip().replace(" + ", " ")
    retrieval = {
        "query": query,
        "status": None,
        "count": 0,
        "total_count": None,
        "chunks": [],
        "error": None,
    }
    documents: list[dict] = []
    answers: list[str] = []
    total_count = None

    try:
        credential = AzureKeyCredential(key)
        client = SearchClient(endpoint=endpoint, index_name=settings["index_name"], credential=credential)

        search_kwargs = {
            "include_total_count": settings["include_total_count"],
            "top": settings["top"],
            "query_type": settings["query_type"],
            "semantic_configuration_name": settings["semantic_configuration"],
            "query_caption": settings["query_caption"],
            "query_answer": settings["query_answer"],
            "query_answer_count": settings["query_answer_count"],
        }
        if settings["scoring_statistics_global"]:
            search_kwargs["scoring_statistics"] = "global"
        if settings["use_session_id"] and session_id:
            search_kwargs["session_id"] = session_id

        # Older azure-search-documents builds do not expose query_language.
        if "query_language" in inspect.signature(client.search).parameters:
            search_kwargs["query_language"] = settings["query_language"]

        print(f"Executing Azure AI Search with query: '{query}' ")
        results = client.search(
            search_text=query,
            **search_kwargs,
        )

        if settings["include_total_count"]:
            total_count = results.get_count()

        for answer in results.get_answers() or []:
            answer_text = getattr(answer, "text", None)
            if answer_text:
                answers.append(answer_text)

        for result in results:
            captions = []
            for caption in result.get("@search.captions") or []:
                caption_text = getattr(caption, "text", None) if not isinstance(caption, dict) else caption.get("text")
                if caption_text:
                    captions.append(caption_text)
            documents.append({
                "id": result.get("chunk_id") or result.get("id"),
                "score": result.get("@search.score"),
                "reranker_score": result.get("@search.reranker_score", result.get("@search.rerankerScore")),
                "content": str(result.get("content") or result.get("text") or result.get("chunk") or result),
                "captions": captions,
            })
        retrieval["status"] = 200
    except HttpResponseError as e:
        retrieval["status"] = e.status_code
        retrieval["error"] = str(e)
    except Exception as e:
        retrieval["error"] = str(e)

    retrieval["count"] = len(documents)
    retrieval["total_count"] = total_count
    retrieval["chunks"] = [
        {"id": doc["id"], "score": doc["score"], "reranker_score": doc["reranker_score"]}
        for doc in documents
    ]
    if retrieval["error"]:
        logger.error("Azure AI Search query failed: %s", json.dumps(retrieval))
    elif not documents:
        logger.error("Azure AI Search returned 0 results: %s", json.dumps(retrieval))
    print(f"Azure AI Search retrieval: {json.dumps(retrieval)}")
    return documents, answers, total_count, retrieval


def order_documents(documents: list[dict]) -> list[dict]:
    """Deterministic prompt order: reranker score desc, then search score desc, then chunk id."""
    return sorted(
        documents,
        key=lambda doc: (
            -(doc["reranker_score"] or 0.0),
            -(doc["score"] or 0.0),
            str(doc["id"] or ""),
        ),
    )


def format_results(documents: list[dict], answers: list[str], total_count: int | None, client_settings: dict) -> str:
    """Render search results as the tool output text the LLM sees."""
    settings = _search_settings(client_settings)
    output = []

    if total_count is not None:
        output.append(f"Total count: {total_count}")

    for answer_text in answers:
        output.append(f"Answer: {answer_text}")

    for doc in documents:
        for caption_text in doc["captions"]:
            output.append(f"Caption: {caption_text}")

        if settings["enable_trimming"]:
            output.append(f"Content: {doc['content'][:settings['trim_length']]}...")
        else:
            output.append(f"Content: {doc['content']}")
    print(f"Azure AI Search Tool results: {output}")
    return "\n\n".join(output) if output else "No results found."


def run_search(query: str, client_settings: dict, session_id: str | None = None) -> tuple[str, dict]:
    """Search and build the tool output. Returns (tool_text, retrieval)."""
    documents, answers, total_count, retrieval = search_documents(query, client_settings, session_id=session_id)
    if retrieval["error"]:
        print(f"Error executing search: {retrieval['error']}")
        return f"Error executing search: {retrieval['error']}", retrieval

    if _search_settings(client_settings)["deterministic_order"]:
        documents = order_documents(documents)
        retrieval["prompt_order"] = [doc["id"] for doc in documents]
    return format_results(documents, answers, total_count, client_settings), retrieval


@tool(
    name="azure_ai_search",
    description="Retrieves information related with Permit Applications using Azure AI Search",
)
def azure_ai_search(query: str, client_settings: dict) -> str:
    """Retrieves information related with BC government permit application."""
    return run_search(query, client_settings)[0]
