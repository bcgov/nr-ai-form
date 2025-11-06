import json
import os
import logging
from typing import Optional, List, TypedDict

from langchain.tools import tool
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from azure.core.exceptions import AzureError
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import ast

load_dotenv()

import re
def extract_message_and_formfields(query: str):
    """
    Extracts message and formFields from a JSON-like or Python dict string.
    Returns (message, formFields) or (query, None) if not parseable.
    """
    if isinstance(query, dict):
        message = query.get("message", "")
        formFields = query.get("formFields", None)
        return message, formFields
    try:
        # Try JSON first
        data = json.loads(query)
    except Exception:
        try:
            # Fallback: use ast.literal_eval for Python-like dicts
            data = ast.literal_eval(query)
        except Exception as e:
            print(f"extract_message_and_formfields error: {e}")
            return query, None
    message = data.get("message", "")
    formFields = data.get("formFields", None)
    return message, formFields

def _get_search_client() -> Optional[SearchClient]:
    """Get or lazily initialize the Azure AI Search client.
    Uses a function attribute for caching to avoid module-level globals.
    Returns None if not configured.
    """
    if hasattr(_get_search_client, "_client"):
        return getattr(_get_search_client, "_client")  # type: ignore[attr-defined]

    search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    search_key = os.environ.get("AZURE_SEARCH_KEY")
    index_name = os.environ.get("AZURE_SEARCH_INDEX_NAME")

    client: Optional[SearchClient] = None
    if search_endpoint and search_key and index_name:
        credential = AzureKeyCredential(search_key)
        client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=credential,
        )
    setattr(_get_search_client, "_client", client)  # type: ignore[attr-defined]
    return client


@tool("ai_search_tool")
def ai_search_tool(query: str) -> str:
    """
    Search and retrieve data from the configured Azure AI Search index.
    Expects the following environment variables to be set:
    - AZURE_SEARCH_ENDPOINT
    - AZURE_SEARCH_KEY
    - AZURE_SEARCH_INDEX_NAME
    """
    import logging
    #import pdb; pdb.set_trace()
    #query = "water licence application"
    client = _get_search_client()
    logging.info(f"ai_search_tool called with query: {query}")

    # Extract message and formFields if query is JSON
    message, formFields = extract_message_and_formfields(query)
    logging.info(f"Extracted message: {message}")
    if formFields:
        logging.info(f"Extracted formFields: {formFields}")
    
    if client is None:
        return (
            "Azure Search not configured. Please set AZURE_SEARCH_ENDPOINT, "
            "AZURE_SEARCH_KEY, and AZURE_SEARCH_INDEX_NAME."
        )

    try:
        # Build filter string from formFields
        filters = []
        if formFields and isinstance(formFields, list):
            for field in formFields:
                # Check if field is a dict with data_id and field_value keys
                field_id = field.get("data_id")
                field_value = field.get("fieldValue")
                
                if field_id and field_value:
                    safe_value = str(field_value).replace("'", "''")
                    filters.append(f"{field_id} eq '{safe_value}'")
        
        filter_str = " and ".join(filters) if filters else None
        if filter_str:
            logging.info(f"Azure Search filter: {filter_str}")
            
        # Prepare search arguments
        search_args = {
            "search_text": message,
            "select": ["*"],
            "top": 3,
        }
        
        if filter_str:
            search_args["filter"] = filter_str
        
        search_results = client.search(**search_args)
        results = [dict(r) for r in search_results]
        
        if not results:
            return f"No results found for query '{message}'" + (f" with filters: {filter_str}" if filter_str else "")
        
        # Return a concise string representation of results
        return str(results)
    except AzureError as e:
        return f"Error searching index: {str(e)}"    

    # if client is None:
    #     return (
    #         "Azure Search not configured. Please set AZURE_SEARCH_ENDPOINT, "
    #         "AZURE_SEARCH_KEY, and AZURE_SEARCH_INDEX_NAME."
    #     )

    # # Build filter string from formFields
    # filters = []
    # if formFields and isinstance(formFields, list):
    #     for field in formFields:
    #         value = field.get("field_value")
    #         if value:
    #             safe_value = str(value).replace("'", "''")
    #             filters.append(f"{field['data_id']} eq '{safe_value}'")
    # filter_str = " and ".join(filters) if filters else None
    # if filter_str:
    #     logging.info(f"Azure Search filter: {filter_str}")

    # try:
    #     search_args = {
    #         "search_text": message,
    #         "select": ["*"],
    #         "search_mode": "hybrid",
    #         "top": 5,
    #     }
    #     # if filter_str:
    #     #     search_args["filter"] = filter_str
    #     search_results = client.search(**search_args)
    #     results = [dict(r) for r in search_results]
    #     if not results:
    #         return f"No results found for query '{message}' with filters: {filter_str}"
    #     return str(results)
    # except AzureError as e:
    #     return f"Error searching index: {str(e)}"

# @tool("ai_search_tool")
# def ai_search_tool(query: str) -> str:
#     """
#     Search and retrieve data from the configured Azure AI Search index.
#     Expects the following environment variables to be set:
#     - AZURE_SEARCH_ENDPOINT
#     - AZURE_SEARCH_KEY
#     - AZURE_SEARCH_INDEX_NAME
#     """
#     client = _get_search_client()
#     #logger.info("Azure Search client initialized.")

#     if client is None:
#         return (
#             "Azure Search not configured. Please set AZURE_SEARCH_ENDPOINT, "
#             "AZURE_SEARCH_KEY, and AZURE_SEARCH_INDEX_NAME."
#         )

#     try:
#         search_results = client.search(
#             search_text=query,
#             select=["*"],
#             search_mode="hybrid",
#             top=5,
#         )
#         results = [dict(r) for r in search_results]
#         #logger.info("Search results count=%d", len(results))
#         if not results:
#             return f"No results found for query '{query}'"
#         # Return a concise string representation of results
#         return str(results)
#     except AzureError as e:
#         return f"Error searching index: {str(e)}"


