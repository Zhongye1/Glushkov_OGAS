from fastapi import APIRouter

from src.api.rag import router as rag_router

api_router = APIRouter()
api_router.include_router(rag_router)
