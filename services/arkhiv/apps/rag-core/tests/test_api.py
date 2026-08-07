from httpx import ASGITransport, AsyncClient

from src.api.app import app


async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_retrieve_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/retrieve", json={"query": "OGAS"})
    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert body[0]["source_path"]
