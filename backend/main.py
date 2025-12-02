"""
Main FastAPI application with POST endpoint backbone
"""

import os
import logging
from fastapi import FastAPI
from backend.formfiller.api import router as api_router
from dotenv import load_dotenv
from backend.search_indexer import web_crawler

load_dotenv()

# Configure logging (honor LOG_LEVEL env var; default INFO)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_level = getattr(logging, LOG_LEVEL, logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(_level)

# Ensure at least one handler is configured so logs are emitted when launched via uv/uvicorn
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


# Initialize FastAPI app
app = FastAPI(
    title="NR Agentic AI API",
    description=(
        "An agentic AI API built with FastAPI, LangGraph, and LangChain. "
        "Features intelligent form filling and multi-agent workflows."
    ),
    version="0.1.0"
)

# Log app init once
logger.info("NR Agentic AI API initialized (log level=%s)", LOG_LEVEL)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "NR Agentic AI API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "NR Agentic AI API"}

@app.get("/indexer")
async def start_indexing():
    web_crawler.start_indexing()
    return {"message": "Indexing started"}

@app.get("/indexer/test")
async def test_index_single_file():
    """Test endpoint to index the BCeID file specifically"""
    try:
        result = web_crawler.index_single_file(
            blob_name="BCeIDTypesofBCeID.pdf",
            file_url="https://cssaidevhub27077213787.blob.core.windows.net/source-docs-posse/BCeIDTypesofBCeID.pdf"
        )
        return result
    except Exception as e:
        logger.error(f"Error in test indexing: {e}", exc_info=True)
        return {"error": str(e), "status": "failed"}

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=LOG_LEVEL.lower())