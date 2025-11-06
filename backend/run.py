#!/usr/bin/env python3
"""
Simple script to run the FastAPI application
"""

import uvicorn
from src.nr_agentic_ai_api.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
