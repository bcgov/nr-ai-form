from pathlib import Path
import json
import uvicorn

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Or ["*"] to allow all origins
    allow_credentials=True,
    allow_methods=["*"],             # Allows all standard HTTP methods (GET, POST, etc.)
    allow_headers=["*"],             # Allows all headers
)

# Folder containing the JSON files
JSON_FOLDER = Path("C:\\Users\\krish\\Downloads\\bcgov\\nr-ai-form\\agentic_ai_backend\\agents\\formsupportagent\\formdefinitions")


@app.get("/get-json")
def get_json(step_number: str):
    """
    Example:
    GET /get-json?step_number=1

    Reads:
    /path/to/json/files/1.json
    """

    file_path = JSON_FOLDER / f"{step_number}.json"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path.name}"
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON in file: {file_path.name}"
        )
    

if __name__ == "__main__":
    print(f"Starting File server on port 8003")
    uvicorn.run(app, host="0.0.0.0", port=8003)