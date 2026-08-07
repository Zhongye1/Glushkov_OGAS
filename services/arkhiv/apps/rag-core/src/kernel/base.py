from collections.abc import AsyncIterator
from typing import Protocol

from src.api.schemas import Answer, Chunk


class RAGKernel(Protocol):
    async def retrieve(
        self, query: str, top_k: int = 10, filters: dict[str, str] | None = None
    ) -> list[Chunk]: ...

    async def answer(
        self, query: str, top_k: int = 10, filters: dict[str, str] | None = None
    ) -> Answer: ...

    def stream(
        self, query: str, top_k: int = 10, filters: dict[str, str] | None = None
    ) -> AsyncIterator[str]: ...


class InMemoryKernel:
    """占位实现，用于打通协议层；检索/生成链路待按 RAG.md 接入。"""

    async def retrieve(
        self, query: str, top_k: int = 10, filters: dict[str, str] | None = None
    ) -> list[Chunk]:
        return [
            Chunk(
                text=f"关于「{query}」的占位片段",
                source_path="docs/RAG.md",
                line_range=(1, 5),
                score=1.0,
            )
        ][:top_k]

    async def answer(
        self, query: str, top_k: int = 10, filters: dict[str, str] | None = None
    ) -> Answer:
        chunks = await self.retrieve(query, top_k=top_k, filters=filters)
        return Answer(text=f"基于 {len(chunks)} 条片段的占位回答", citations=chunks)

    async def stream(
        self, query: str, top_k: int = 10, filters: dict[str, str] | None = None
    ) -> AsyncIterator[str]:
        for token in ["占位", "回答", "，", "待接入", "真实", "链路"]:
            yield token
