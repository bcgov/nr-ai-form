from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import inspect
import os

from agent_framework import ai_function


@ai_function(name="azure_ai_search", description="Retrieves information related with Permit Applications using Azure AI Search")
def azure_ai_search(query: str) -> str:
    """
        Retrieves information related with BC government permit application
    """
    try:
        print("Azure AI Search Tool calling...")
        endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        key = os.environ["AZURE_SEARCH_API_KEY"]
        index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]
        
        top_value = int(os.getenv("AZURE_SEARCH_TOP", 3))
        trim_length = int(os.getenv("AZURE_SEARCH_TRIM_LENGTH", 500))
        enable_trimming = os.getenv("AZURE_SEARCH_ENABLE_TRIMMING", "true").lower() == "true"
        include_total_count = os.getenv("AZURE_SEARCH_INCLUDE_TOTAL_COUNT", "true").lower() == "true"
        query_type = os.getenv("AZURE_SEARCH_QUERY_TYPE", "semantic")
        semantic_configuration = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIGURATION", "semanticconfig")
        query_caption = os.getenv("AZURE_SEARCH_QUERY_CAPTION", "extractive")
        query_answer = os.getenv("AZURE_SEARCH_QUERY_ANSWER", "extractive")
        query_answer_count = int(os.getenv("AZURE_SEARCH_QUERY_ANSWER_COUNT", 3))
        query_language = os.getenv("AZURE_SEARCH_QUERY_LANGUAGE", "en-us")

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
            # Try to grab content from common field names
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
        
        return "\n\n".join(output) if output else "No results found."
    except Exception as e:
        print(f"Error executing search: {e}")
        return f"Error executing search: {e}"
