from fastapi import APIRouter
from backend.search_indexer import web_crawler
router = APIRouter()


@router.get("/")
async def start_indexing():
    web_crawler.start_indexing()
    return {"message": "Indexing started"}