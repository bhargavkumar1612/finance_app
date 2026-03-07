"""Integration tests: health endpoint."""
import pytest
from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
