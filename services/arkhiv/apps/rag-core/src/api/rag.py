import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.kernel import Answer, Chunk, RAGKernel, get_kernel

router = APIRouter(tags=["rag"])

KernelDep = Annotated[RAGKernel, Depends(get_kernel)]


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: dict[str, str] | None = None


class AnswerRequest(RetrieveRequest):
    stream: bool = False


@router.post("/retrieve", response_model=list[Chunk])
async def retrieve(req: RetrieveRequest, kernel: KernelDep) -> list[Chunk]:
    return await kernel.retrieve(req.query, top_k=req.top_k, filters=req.filters)


@router.post("/answer", response_model=Answer)
async def answer(req: AnswerRequest, kernel: KernelDep) -> Answer | StreamingResponse:
    if not req.stream:
        return await kernel.answer(req.query, top_k=req.top_k, filters=req.filters)

    async def event_stream() -> AsyncIterator[str]:
        async for token in kernel.stream(req.query, top_k=req.top_k, filters=req.filters):
            yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
