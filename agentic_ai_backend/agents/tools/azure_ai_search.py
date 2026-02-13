from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os

# Define a no-op decorator for ai_function since it's not available in agent_framework
def ai_function(name=None, description=None):
    def decorator(func):
        return func
    return decorator

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
        
        credential = AzureKeyCredential(key)
        client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
        
        # Simple search execution
        results = client.search(search_text=query, top=3)
        
        output = []        
        for result in results:
            # Try to grab content from common field names
            content = result.get("content") or result.get("text") or result.get("chunk") or str(result)
            output.append(f"Content: {str(content)[:500]}...")
        
        return "\n\n".join(output) if output else "No results found."
    except Exception as e:
        print(f"Error executing search: {e}")
        return f"Error executing search: {e}"