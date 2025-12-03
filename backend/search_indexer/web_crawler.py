"""
Web Crawler and Document Indexer using Azure Document Intelligence

This module processes documents from Azure Blob Storage using Azure Document Intelligence
for advanced document parsing and analysis, then indexes them in Azure AI Search.

Required Environment Variables:
- AZURE_STORAGE_ACCOUNT_NAME: Azure Storage Account name
- AZURE_STORAGE_ACCOUNT_KEY: Azure Storage Account access key
- AZURE_STORAGE_CONTAINER_NAME: Container name containing documents
- AZURE_SEARCH_ENDPOINT: Azure AI Search service endpoint
- AZURE_SEARCH_ADMIN_KEY: Azure AI Search admin key
- AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: Document Intelligence service endpoint
- AZURE_DOCUMENT_INTELLIGENCE_KEY: Document Intelligence service key (optional if using managed identity)
"""

from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os
from azure.storage.blob import BlobServiceClient
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeDocumentRequest,
    DocumentContentFormat,
)
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.exceptions import HttpResponseError
import traceback
import time
from typing import List
from backend.core.logging import get_logger
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in backend directory
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / ".env"
load_dotenv(dotenv_path=env_file)

# Initialize structured logger
logger = get_logger(__name__)


# Environment variables (will be set in Azure Functions later)
AZURE_STORAGE_CONNECTION_STRING = f"DefaultEndpointsProtocol=https;AccountName={os.getenv('AZURE_STORAGE_ACCOUNT_NAME')};AccountKey={os.getenv('AZURE_STORAGE_ACCOUNT_KEY')};EndpointSuffix=core.windows.net"
blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING
)
container_client = blob_service_client.get_container_client(
    os.getenv("AZURE_STORAGE_CONTAINER_NAME")
)

# Initialize Document Intelligence client
document_intelligence_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
document_intelligence_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

# Use key-based authentication if available, otherwise use DefaultAzureCredential
if document_intelligence_key:
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint=document_intelligence_endpoint,
        credential=AzureKeyCredential(document_intelligence_key),
    )
else:
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint=document_intelligence_endpoint, credential=DefaultAzureCredential()
    )

# Lazy initialization for Azure services
_embeddings = None
_vector_store = None

def get_embeddings():
    """Get Azure OpenAI embeddings client with lazy initialization."""
    global _embeddings
    if _embeddings is None:
        _embeddings = AzureOpenAIEmbeddings(
            azure_deployment="text-embedding-3-large",  # Deploy this embedding model in Azure OpenAI if not already (similar to GPT deployment)
            openai_api_version="2024-02-01",  # Adjust to latest
        )
    return _embeddings

def get_vector_store():
    """Get Azure Search vector store with lazy initialization."""
    global _vector_store
    if _vector_store is None:
        _vector_store = AzureSearch(
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            azure_search_key=os.getenv("AZURE_SEARCH_ADMIN_KEY"),
            index_name="bc-water-index",  # Create if doesn't exist
            embedding_function=get_embeddings().embed_query,
            search_type="hybrid",  # Enables vector + keyword
        )
    return _vector_store


def verify_indexing(index_name="bc-water-index", wait_seconds=3):
    """
    Verify that documents have been successfully indexed.
    
    Args:
        index_name: Name of the search index
        wait_seconds: Seconds to wait for indexing to complete
        
    Returns:
        Dictionary with verification results
    """
    try:
        # Wait for indexing to complete
        logger.info(f"Waiting {wait_seconds} seconds for indexing to complete...")
        time.sleep(wait_seconds)
        
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("AZURE_SEARCH_ADMIN_KEY")
        
        if not search_endpoint or not search_key:
            logger.error("Missing Azure Search credentials for verification")
            return {
                "success": False,
                "error": "Missing Azure Search credentials"
            }
        
        credential = AzureKeyCredential(search_key)
        
        # Get index statistics
        logger.info("Fetching index statistics")
        index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
        stats = index_client.get_index_statistics(index_name)
        
        # Handle both dict and object responses
        if isinstance(stats, dict):
            document_count = stats.get('document_count', 0)
            storage_size = stats.get('storage_size', 0)
        else:
            document_count = getattr(stats, 'document_count', 0)
            storage_size = getattr(stats, 'storage_size', 0)
        
        logger.info(
            "Index statistics retrieved",
            document_count=document_count,
            storage_size=storage_size
        )
        
        # Search for sample documents
        logger.info("Searching for sample documents")
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=credential
        )
        
        # Search for all documents
        results = list(search_client.search(search_text="*", top=5))
        
        logger.info(
            "Sample documents retrieved",
            sample_count=len(results)
        )
        
        # Log sample document previews
        for i, result in enumerate(results, 1):
            content_preview = str(result.get('content', ''))[:100]
            logger.debug(
                f"Sample document {i}",
                content_preview=content_preview
            )
        
        verification_result = {
            "success": True,
            "document_count": document_count,
            "storage_size": storage_size,
            "sample_documents_found": len(results),
            "has_documents": document_count > 0
        }
        
        if document_count > 0:
            logger.info(
                "✅ Indexing verification successful",
                **verification_result
            )
        else:
            logger.warning("⚠️  No documents found in index")
        
        return verification_result
        
    except Exception as e:
        logger.error(
            "Error during indexing verification",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def add_documents_in_batches(vector_store, chunks: List[Document], batch_size: int = 10, max_retries: int = 3):
    """
    Add documents to vector store in smaller batches with retry logic.
    
    Args:
        vector_store: The Azure Search vector store
        chunks: List of document chunks to index
        batch_size: Number of documents per batch (default: 10)
        max_retries: Maximum number of retry attempts per batch (default: 3)
        
    Returns:
        Dictionary with indexing results
    """
    total_chunks = len(chunks)
    successful = 0
    failed = 0
    failed_batches = []
    
    logger.info(
        "Starting batch indexing",
        total_chunks=total_chunks,
        batch_size=batch_size
    )
    
    # Process chunks in batches
    for i in range(0, total_chunks, batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_chunks + batch_size - 1) // batch_size
        
        logger.info(
            f"Processing batch {batch_num}/{total_batches}",
            batch_start=i,
            batch_end=min(i + batch_size, total_chunks)
        )
        
        # Retry logic for each batch
        for attempt in range(max_retries):
            try:
                vector_store.add_documents(batch)
                successful += len(batch)
                logger.info(
                    f"✅ Batch {batch_num} indexed successfully",
                    documents_in_batch=len(batch),
                    attempt=attempt + 1
                )
                break  # Success, move to next batch
                
            except HttpResponseError as e:
                if "Bad Gateway" in str(e) or "502" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                        logger.warning(
                            f"Bad Gateway error on batch {batch_num}, retrying...",
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            wait_seconds=wait_time
                        )
                        time.sleep(wait_time)
                    else:
                        failed += len(batch)
                        failed_batches.append(batch_num)
                        logger.error(
                            f"❌ Batch {batch_num} failed after {max_retries} attempts",
                            error=str(e),
                            documents_in_batch=len(batch)
                        )
                else:
                    # Different error, don't retry
                    failed += len(batch)
                    failed_batches.append(batch_num)
                    logger.error(
                        f"❌ Batch {batch_num} failed with non-retryable error",
                        error=str(e),
                        error_type=type(e).__name__,
                        documents_in_batch=len(batch)
                    )
                    break
                    
            except Exception as e:
                failed += len(batch)
                failed_batches.append(batch_num)
                logger.error(
                    f"❌ Batch {batch_num} failed with unexpected error",
                    error=str(e),
                    error_type=type(e).__name__,
                    documents_in_batch=len(batch),
                    exc_info=True
                )
                break
        
        # Small delay between batches to avoid overwhelming the service
        if i + batch_size < total_chunks:
            time.sleep(0.5)
    
    result = {
        "total_chunks": total_chunks,
        "successful": successful,
        "failed": failed,
        "failed_batches": failed_batches,
        "success_rate": (successful / total_chunks * 100) if total_chunks > 0 else 0
    }
    
    logger.info(
        "Batch indexing completed",
        **result
    )
    
    return result


def process_document_with_intelligence(blob_name, blob_data):
    """
    Process a document using Azure Document Intelligence.
    
    Sends the document bytes directly to Document Intelligence (not via URL)
    to avoid issues with private blob storage endpoints.
    
    Returns a Document object with the extracted content
    """
    try:
        logger.info(
            "Processing document with Document Intelligence",
            blob_name=blob_name,
            file_size=len(blob_data)
        )
        
        # Create the request with the blob data bytes
        # This sends the document content directly, avoiding blob URL access issues
        analyze_request = AnalyzeDocumentRequest(bytes_source=blob_data)

        # Use the prebuilt-read model for general document reading
        # For tables and forms, consider using "prebuilt-layout"
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-read",
            analyze_request,
            output_content_format=DocumentContentFormat.MARKDOWN,
        )
        
        # Wait for the analysis to complete
        result = poller.result()

        # Extract the content
        content = result.content if result.content else ""
        
        if not content:
            logger.warning(
                "Document Intelligence returned empty content",
                blob_name=blob_name
            )
            return None

        logger.info(
            "Successfully processed document",
            blob_name=blob_name,
            content_length=len(content)
        )

        # Create a Document object
        return Document(
            page_content=content,
            metadata={
                "source": blob_name,
                "processed_with": "azure_document_intelligence",
                "file_size": len(blob_data),
            },
        )
        
    except HttpResponseError as e:
        # Handle specific HTTP errors
        if "403" in str(e) or "Forbidden" in str(e):
            logger.error(
                "Document Intelligence access forbidden - check endpoint configuration",
                blob_name=blob_name,
                error=str(e),
                suggestion="Verify AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and KEY are correct"
            )
        elif "401" in str(e) or "Unauthorized" in str(e):
            logger.error(
                "Document Intelligence authentication failed",
                blob_name=blob_name,
                error=str(e),
                suggestion="Check AZURE_DOCUMENT_INTELLIGENCE_KEY is valid"
            )
        else:
            logger.error(
                "Document Intelligence HTTP error",
                blob_name=blob_name,
                error=str(e),
                status_code=getattr(e, 'status_code', 'unknown'),
                error_type=type(e).__name__,
                exc_info=True,
            )
        return None
        
    except Exception as e:
        logger.error(
            "Unexpected error processing document with Document Intelligence",
            blob_name=blob_name,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return None


def start_indexing():
    try:
        # Load and chunk documents
        docs = []
        logger.info("Starting document loading from blob storage")

        for blob in container_client.list_blobs():
            try:
                # Get the blob data
                blob_client = container_client.get_blob_client(blob.name)
                blob_data = blob_client.download_blob().readall()

                if blob.name.endswith((".pdf", ".docx", ".doc", ".txt", ".html", ".json")):
                    logger.info("Processing document", blob_name=blob.name)

                    # Use Document Intelligence to process the document
                    document = process_document_with_intelligence(blob.name, blob_data)

                    if document:
                        docs.append(document)
                        logger.info(
                            "Successfully processed document", blob_name=blob.name
                        )
                    else:
                        logger.warning(
                            "Failed to process document", blob_name=blob.name
                        )

                else:
                    logger.debug("Skipping unsupported file type", blob_name=blob.name)

            except Exception as blob_error:
                logger.error(
                    "Error processing blob",
                    blob_name=blob.name,
                    error=str(blob_error),
                    error_type=type(blob_error).__name__,
                    exc_info=True,
                )
                continue

        # Example for webpage
        try:
            logger.info("Loading webpage")
            web_loader = WebBaseLoader(
                "https://portalext.nrs.gov.bc.ca/web/client/-/unit-converter"
            )
            docs.extend(web_loader.load())
            logger.info("Successfully loaded webpage")
        except Exception as web_error:
            logger.error(
                "Error loading webpage",
                error=str(web_error),
                error_type=type(web_error).__name__,
                exc_info=True,
            )

        logger.info("Document loading completed", total_documents=len(docs))

        # Add more loaders for other files...
        logger.info("Starting text splitting")
        splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
        chunks = splitter.split_documents(docs)
        logger.info("Text splitting completed", total_chunks=len(chunks))

        # Index with batch processing and retry logic
        logger.info("Starting vector store indexing with batch processing")
        vector_store = get_vector_store()
        
        # Use smaller batches to avoid Bad Gateway errors
        indexing_result = add_documents_in_batches(
            vector_store=vector_store,
            chunks=chunks,
            batch_size=10,  # Process 10 documents at a time
            max_retries=3    # Retry up to 3 times per batch
        )
        
        logger.info("Vector store indexing completed")

        # Verify indexing
        logger.info("Starting indexing verification")
        verification_result = verify_indexing()
        
        return {
            "message": "Indexing completed successfully",
            "documents_processed": len(docs),
            "chunks_created": len(chunks),
            "indexing_result": indexing_result,
            "verification": verification_result
        }

    except Exception as e:
        logger.error(
            "Critical error during indexing",
            error=str(e),
            error_type=type(e).__name__,
            full_traceback=traceback.format_exc(),
            exc_info=True,
        )
        return {"error": f"Indexing failed: {str(e)}"}


def index_single_file(blob_name: str, file_url: str = None):
    """
    Index a single file from blob storage
    
    Args:
        blob_name: Name of the blob file (e.g., "BCeIDTypesofBCeID.pdf")
        file_url: Optional direct URL to the file
        
    Returns:
        dict: Result of indexing operation
    """
    try:
        logger.info("Starting single file indexing", blob_name=blob_name, file_url=file_url)
        
        # Get the blob data
        blob_client = container_client.get_blob_client(blob_name)
        blob_data = blob_client.download_blob().readall()
        
        logger.info("Successfully downloaded blob", blob_name=blob_name, size_bytes=len(blob_data))
        
        # Process with Document Intelligence
        logger.info("Processing document with Document Intelligence", blob_name=blob_name)
        document = process_document_with_intelligence(blob_name, blob_data)
        
        if not document:
            error_msg = f"Failed to process document: {blob_name}"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "blob_name": blob_name
            }
        
        logger.info("Successfully processed document", blob_name=blob_name, content_length=len(document.page_content))
        
        # Split into chunks
        logger.info("Starting text splitting")
        splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
        chunks = splitter.split_documents([document])
        logger.info("Text splitting completed", total_chunks=len(chunks))
        
        # Index chunks
        logger.info("Starting vector store indexing")
        vector_store = get_vector_store()
        
        # Use batch processing for reliability
        indexing_result = add_documents_in_batches(
            vector_store=vector_store,
            chunks=chunks,
            batch_size=10,
            max_retries=3
        )
        
        logger.info("Vector store indexing completed", indexing_result=indexing_result)
        
        # Verify by searching
        logger.info("Verifying indexing by searching")
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("AZURE_SEARCH_ADMIN_KEY")
        search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "bc-water-index")
        
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=search_index_name,
            credential=AzureKeyCredential(search_key)
        )
        
        # Search for BCeID to verify
        results = search_client.search("BCeID", top=3)
        found_results = list(results)
        
        return {
            "status": "success",
            "blob_name": blob_name,
            "file_url": file_url,
            "document_processed": True,
            "content_length": len(document.page_content),
            "chunks_created": len(chunks),
            "indexing_result": indexing_result,
            "verification": {
                "search_query": "BCeID",
                "results_found": len(found_results),
                "sample_results": [
                    {
                        "title": r.get("title", "N/A"),
                        "score": r.get("@search.score", 0)
                    }
                    for r in found_results[:3]
                ]
            }
        }
        
    except Exception as e:
        logger.error(
            "Error indexing single file",
            blob_name=blob_name,
            error=str(e),
            error_type=type(e).__name__,
            full_traceback=traceback.format_exc(),
            exc_info=True
        )
        return {
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__,
            "blob_name": blob_name
        }

