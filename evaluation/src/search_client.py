"""Azure AI Search client for retrieval."""

import logging
import inspect
from typing import Optional, Dict, Any
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

from src.config import settings

logger = logging.getLogger(__name__)


class AzureSearchContextRetriever:
    """Retrieve evaluation context from Azure AI Search."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
    ):
        """
        Initialize Azure Search retriever.
        
        Args:
            endpoint: Azure Search endpoint (uses settings if not provided)
            api_key: Azure Search API key (uses settings if not provided)
            index_name: Index name (uses settings if not provided)
        """
        self.endpoint = endpoint or settings.azure_search_endpoint
        self.api_key = api_key or settings.azure_search_api_key
        self.index_name = index_name or settings.azure_search_index_name
        
        # Search configuration from settings
        self.top = settings.azure_search_top
        self.trim_length = settings.azure_search_trim_length
        self.enable_trimming = settings.azure_search_enable_trimming
        self.include_total_count = settings.azure_search_include_total_count
        self.query_type = settings.azure_search_query_type
        self.semantic_configuration = settings.azure_search_semantic_configuration
        self.query_caption = settings.azure_search_query_caption
        self.query_answer = settings.azure_search_query_answer
        self.query_answer_count = settings.azure_search_query_answer_count
        self.query_language = settings.azure_search_query_language
        
        # Validate configuration
        if not self.endpoint or not self.api_key or not self.index_name:
            raise ValueError(
                "Azure Search configuration missing: "
                "endpoint, api_key, and index_name are required"
            )
        
        # Initialize search client
        self.client = self._init_client()
        logger.info(
            f"Search retriever initialized - endpoint: {self.endpoint}, "
            f"index: {self.index_name}, query_type: {self.query_type}"
        )

    def _init_client(self) -> SearchClient:
        """Initialize SearchClient."""
        credential = AzureKeyCredential(self.api_key)
        return SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=credential,
        )

    def retrieve_context(self, query: str) -> str:
        """
        Retrieve context for evaluation from Azure Search.
        
        Args:
            query: Search query/question
            
        Returns:
            Combined context from search results
        """
        # Try semantic search first, fallback to simple if semantic not configured
        return self._execute_search_with_fallback(query)

    def _execute_search_with_fallback(self, query: str) -> str:
        """
        Execute search with fallback from semantic to simple query.
        
        Args:
            query: Search query/question
            
        Returns:
            Combined context from search results
        """
        # First attempt: try semantic search if configured
        if self.query_type == "semantic":
            try:
                return self._execute_search(query, query_type="semantic")
            except Exception as e:
                error_msg = str(e).lower()
                # Check if error is due to missing semantic configuration
                if "semantic" in error_msg and "configuration" in error_msg:
                    logger.warning(
                        f"Semantic search not configured: {str(e)}. "
                        "Falling back to simple search."
                    )
                    # Fallback to simple search
                    return self._execute_search(query, query_type="simple")
                else:
                    # Re-raise other errors
                    raise
        else:
            # Use simple search
            return self._execute_search(query, query_type="simple")

    def _execute_search(self, query: str, query_type: str = "simple") -> str:
        """
        Execute search with specified query type.
        
        Args:
            query: Search query/question
            query_type: Type of search - 'simple' or 'semantic'
            
        Returns:
            Combined context from search results
        """
        try:
            # Build search kwargs based on query type
            search_kwargs = {
                "include_total_count": self.include_total_count,
                "top": self.top,
                "query_type": query_type,
            }
            
            # Add semantic-specific parameters only for semantic search
            if query_type == "semantic":
                search_kwargs["semantic_configuration_name"] = self.semantic_configuration
                search_kwargs["query_caption"] = self.query_caption
                search_kwargs["query_answer"] = self.query_answer
                search_kwargs["query_answer_count"] = self.query_answer_count
            
            # Add query_language if supported by SDK version
            if "query_language" in inspect.signature(self.client.search).parameters:
                search_kwargs["query_language"] = self.query_language
            
            # Execute search - note: error may occur when accessing results, not on call
            results = self.client.search(search_text=query, **search_kwargs)
            
            # Process results - this is where semantic config errors surface
            try:
                # Collect output
                output = []
                
                # Add total count
                if self.include_total_count:
                    total_count = results.get_count()
                    if total_count is not None:
                        output.append(f"Total Results: {total_count}")
                
                # Add semantic answers (only for semantic search)
                if query_type == "semantic":
                    semantic_answers = results.get_answers()
                    if semantic_answers:
                        for answer in semantic_answers:
                            answer_text = getattr(answer, "text", None)
                            if answer_text:
                                output.append(f"Answer: {answer_text}")
                
                # Add search results
                for result in results:
                    # Extract content from common field names
                    content = (
                        result.get("content")
                        or result.get("text")
                        or result.get("chunk")
                        or str(result)
                    )
                    
                    # Add captions if available (for semantic search)
                    if query_type == "semantic":
                        captions = result.get("@search.captions") or []
                        for caption in captions:
                            caption_text = (
                                getattr(caption, "text", None)
                                if not isinstance(caption, dict)
                                else caption.get("text")
                            )
                            if caption_text:
                                output.append(f"Caption: {caption_text}")
                    
                    # Add content
                    if self.enable_trimming:
                        output.append(f"Content: {str(content)[:self.trim_length]}...")
                    else:
                        output.append(f"Content: {str(content)}")
                
            except Exception as results_error:
                # Check if this is a semantic configuration error
                error_msg = str(results_error).lower()
                if query_type == "semantic" and "semantic" in error_msg and "configuration" in error_msg:
                    logger.warning(
                        f"Semantic search not configured: {results_error}. "
                        "Falling back to simple search."
                    )
                    # Recursively call with simple search
                    return self._execute_search(query, query_type="simple")
                else:
                    # Re-raise if it's a different error
                    raise
            
            result_text = "\n\n".join(output) if output else "No results found."
            logger.info(
                f"Context retrieved - query: {query}, query_type: {query_type}, "
                f"results_count: {len(output)}"
            )
            
            return result_text
            
        except Exception as e:
            logger.exception(
                f"Context retrieval failed for query_type: {query_type}"
            )
            raise
