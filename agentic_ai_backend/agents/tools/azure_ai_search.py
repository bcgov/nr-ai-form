from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
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

        credential = AzureKeyCredential(key)
        client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
        
        # Simple search execution
        results = client.search(search_text=query, top=top_value)
        
        output = []        
        for result in results:
            # Try to grab content from common field names
            content = result.get("content") or result.get("text") or result.get("chunk") or str(result)
            if enable_trimming:
                output.append(f"Content: {str(content)[:trim_length]}...")
            else:
                output.append(f"Content: {str(content)}")
        
        return "\n\n".join(output) if output else "No results found."
    except Exception as e:
        print(f"Error executing search: {e}")
        return f"Error executing search: {e}"