import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import grpc
import pytest
from fastapi.testclient import TestClient
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from farmplan_gateway import main as gateway


@pytest.mark.parametrize("service", ["identity", "farm", "catalog", "planning", "analysis", "media"])
@pytest.mark.parametrize("status", ["unavailable", "not_serving"])
def test_degraded_service_returns_503(monkeypatch, service, status):
    async def check(address):
        return status if address == gateway.HEALTH_SERVICE_ADDRESSES[service] else "ok"

    monkeypatch.setattr(gateway, "check_service_health", check)
    response = TestClient(gateway.app).get("/health")
    assert response.status_code == 503
    assert response.json() == {
        "status": "error", "service": "api-gateway",
        "services": {"gateway": "ok", **{
            name: status if name == service else "ok"
            for name in gateway.HEALTH_SERVICE_ADDRESSES
        }},
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("result,expected", [
    (health_pb2.HealthCheckResponse.SERVING, "ok"),
    (health_pb2.HealthCheckResponse.NOT_SERVING, "not_serving"),
    (health_pb2.HealthCheckResponse.UNKNOWN, "not_serving"),
    (health_pb2.HealthCheckResponse.SERVICE_UNKNOWN, "not_serving"),
    (grpc.RpcError("private-host"), "unavailable"),
    (RuntimeError("private-host"), "unavailable"),
])
async def test_protocol_deadline_and_channel_cleanup(monkeypatch, result, expected):
    channel = AsyncMock()
    channel.__aenter__.return_value = channel
    monkeypatch.setattr(gateway.grpc.aio, "insecure_channel", lambda address: channel)
    check = AsyncMock()
    if isinstance(result, Exception):
        check.side_effect = result
    else:
        check.return_value = health_pb2.HealthCheckResponse(status=result)
    monkeypatch.setattr(gateway.health_pb2_grpc, "HealthStub", lambda channel: SimpleNamespace(Check=check))
    assert await gateway.check_service_health("private-host") == expected
    request = check.call_args.args[0]
    assert request.service == ""
    assert check.call_args.kwargs == {"timeout": 1.0}
    channel.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_checks_run_concurrently(monkeypatch):
    started = set()
    ready = asyncio.Event()

    async def check(address):
        started.add(address)
        if len(started) == 6:
            ready.set()
        await asyncio.wait_for(ready.wait(), timeout=0.5)
        return "ok"

    monkeypatch.setattr(gateway, "check_service_health", check)
    response = await gateway.health()
    assert response.status_code == 200
    assert len(started) == 6


@pytest.mark.asyncio
async def test_outer_deadline_closes_channel(monkeypatch):
    channel = AsyncMock()
    channel.__aenter__.return_value = channel
    monkeypatch.setattr(gateway.grpc.aio, "insecure_channel", lambda address: channel)

    async def blocked(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(gateway.health_pb2_grpc, "HealthStub", lambda channel: SimpleNamespace(Check=blocked))
    monkeypatch.setattr(gateway, "HEALTH_CHECK_TIMEOUT", 0.02)
    assert await asyncio.wait_for(gateway.check_service_health("private-host"), 0.5) == "unavailable"
    channel.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_channel_creation_error_is_sanitized(monkeypatch):
    def broken(address):
        raise RuntimeError("private-host details")

    monkeypatch.setattr(gateway.grpc.aio, "insecure_channel", broken)
    response = await gateway.health()
    assert response.status_code == 503
    assert "private-host" not in response.body.decode()
    assert set(json.loads(response.body)["services"].values()) == {"ok", "unavailable"}


@pytest.mark.asyncio
async def test_real_aio_health_protocol_loopback():
    server = grpc.aio.server()
    servicer = health.aio.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    await server.start()
    try:
        assert await gateway.check_service_health(f"127.0.0.1:{port}") == "ok"
        await servicer.set("", health_pb2.HealthCheckResponse.NOT_SERVING)
        assert await gateway.check_service_health(f"127.0.0.1:{port}") == "not_serving"
    finally:
        await server.stop(0)
