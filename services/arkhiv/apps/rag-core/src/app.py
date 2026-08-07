"""FastAPI 应用入口（uvicorn src.app:app）。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.RESTful.health import router as health_router
from src.api.RESTful.router import api_router
from src.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
