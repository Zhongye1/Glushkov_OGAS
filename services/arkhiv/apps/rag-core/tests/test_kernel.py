import pytest

from src.kernel import InMemoryKernel


@pytest.mark.asyncio
async def test_retrieve_returns_chunks() -> None:
    kernel = InMemoryKernel()
    chunks = await kernel.retrieve("什么是 OGAS")
    assert chunks
    assert all(chunk.text and chunk.source_path for chunk in chunks)


@pytest.mark.asyncio
async def test_answer_has_citations() -> None:
    kernel = InMemoryKernel()
    answer = await kernel.answer("什么是 OGAS")
    assert answer.text
    assert answer.citations


@pytest.mark.asyncio
async def test_stream_yields_tokens() -> None:
    kernel = InMemoryKernel()
    tokens = [token async for token in kernel.stream("什么是 OGAS")]
    assert tokens
