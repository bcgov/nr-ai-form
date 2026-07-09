import inspect
import logging
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from agent_framework import tool
from utils.tenantsettings import setting_from_client_config

logger = logging.getLogger(__name__)


def _parse_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).lower() == "true"


@tool(
    name="azure_ai_search",
    description="Retrieves information related with Permit Applications using Azure AI Search",
)
def azure_ai_search(query: str, client_settings: dict) -> str:
    """Retrieves information related with BC government permit application."""
    try:
        endpoint = setting_from_client_config(client_settings, "azureSearchEndpoint", required=True)
        key = setting_from_client_config(client_settings, "azureSearchApiKey", required=True)
        index_name = setting_from_client_config(client_settings, "azureSearchIndexName", required=True)

        top_value = int(setting_from_client_config(client_settings, "azureSearchTop", default=3))
        trim_length = int(setting_from_client_config(client_settings, "azureSearchTrimLength", default=500))
        enable_trimming = _parse_bool(setting_from_client_config(client_settings, "azureSearchEnableTrimming", default="true"), True)
        include_total_count = _parse_bool(setting_from_client_config(client_settings, "azureSearchIncludeTotalCount", default="true"), True)
        query_type = setting_from_client_config(client_settings, "azureSearchQueryType", default="semantic")
        semantic_configuration = setting_from_client_config(client_settings, "azureSearchSemanticConfiguration", default="semanticconfig")
        query_caption = setting_from_client_config(client_settings, "azureSearchQueryCaption", default="extractive")
        query_answer = setting_from_client_config(client_settings, "azureSearchQueryAnswer", default="extractive")
        query_answer_count = int(setting_from_client_config(client_settings, "azureSearchQueryAnswerCount", default=3))
        query_language = setting_from_client_config(client_settings, "azureSearchQueryLanguage", default="en-us")

        if not endpoint or not key or not index_name:
            raise ValueError("Azure AI Search is not configured: endpoint, api key, and index name are required.")

        credential = AzureKeyCredential(key)
        client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

        search_kwargs = {
            "include_total_count": include_total_count,
            "top": top_value,
            "query_type": query_type,
            "semantic_configuration_name": semantic_configuration,
            "query_caption": query_caption,
            "query_answer": query_answer,
            "query_answer_count": query_answer_count,
        }

        # Older azure-search-documents builds do not expose query_language.
        if "query_language" in inspect.signature(client.search).parameters:
            search_kwargs["query_language"] = query_language

        query = query.strip().replace(" + ", " ")
        print(f"Executing Azure AI Search with query: '{query}' ")
        results = client.search(
            search_text=query,
            **search_kwargs,
        )

        output = []

        if include_total_count:
            total_count = results.get_count()
            if total_count is not None:
                output.append(f"Total count: {total_count}")

        semantic_answers = results.get_answers()
        if semantic_answers:
            for answer in semantic_answers:
                answer_text = getattr(answer, "text", None)
                if answer_text:
                    output.append(f"Answer: {answer_text}")

        for result in results:
            content = result.get("content") or result.get("text") or result.get("chunk") or str(result)
            captions = result.get("@search.captions") or []

            for caption in captions:
                caption_text = getattr(caption, "text", None) if not isinstance(caption, dict) else caption.get("text")
                if caption_text:
                    output.append(f"Caption: {caption_text}")

            if enable_trimming:
                output.append(f"Content: {str(content)[:trim_length]}...")
            else:
                output.append(f"Content: {str(content)}")
        print(f"Azure AI Search Tool results: {output}")
        return "\n\n".join(output) if output else "No results found."
    except ValueError:
        raise
    except Exception as e:
        print(f"Error executing search: {e}")
        logger.warning("Azure AI Search query failed: %s", e)
        return f"Error executing search: {e}"
