"""HTTP acceptance against the real Farm application and synthetic JSON adapter."""
import asyncio
import importlib.util
import json
from pathlib import Path

import grpc
from fastapi.testclient import TestClient
import pytest
from farmplan_gateway import main as gateway
from identity.v1 import identity_pb2

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("farm_application", ROOT / "services/farm-service/src/farmplan_farm/main.py")
farm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(farm)
OWNER = "9a62eedd-7c33-4c4b-b9dc-99b4c7b7e8d4"
ID = "c56c779b-2ee1-4a15-af56-7a3c1c4fb3c8"
HEADERS = {"Authorization": "Bearer test"}


class Error(grpc.RpcError):
    def __init__(self, code):
        self.status = code
    def code(self):
        return self.status


class Context:
    async def abort(self, code, message):
        raise Error(code)


@pytest.fixture
def setup(monkeypatch):
    service = farm.FarmService(farm.JsonStore())
    class Client:
        def __getattr__(self, method):
            return lambda request, timeout=None: asyncio.run(getattr(service, method)(request, Context()))
    class Identity:
        owner = OWNER
        account = "user"
        def GetUser(self, request, timeout=None):
            return identity_pb2.UserProfile(user_id=self.owner, account_type=self.account)
    identity = Identity()
    monkeypatch.setattr(gateway, "farm_client", Client())
    monkeypatch.setattr(gateway, "identity_client", identity)
    return TestClient(gateway.app), service, identity


def test_lifecycle_and_preservation(setup):
    client, service, _ = setup
    result = client.get("/api/v1/farms", headers=HEADERS).json()
    assert result["total"] == 1 and result["pageSize"] == 20
    assert result["items"][0]["summary"] == dict(fieldCount=0, fieldAreaM2=0, activePlanCount=None)
    response = client.patch(f"/api/v1/farms/{ID}", headers=HEADERS, json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert next(iter(service.pool.rows.values()))["data"]["template"]
    created = client.post("/api/v1/farms", headers=HEADERS, json={"name": "New", "contact": {"ownerName": "Synthetic", "email": "synthetic@example.test"}})
    assert created.status_code == 201
    data = created.json()
    assert data["createdAt"] and data["updatedAt"]
    assert client.get(f'/api/v1/farms/{data["id"]}', headers=HEADERS).json() == data
    changed = client.put(f'/api/v1/farms/{data["id"]}', headers=HEADERS, json={"ownerName": "Legacy contact"})
    assert changed.json()["contact"]["ownerName"] == "Legacy contact"
    cleared = client.patch(f'/api/v1/farms/{data["id"]}', headers=HEADERS, json={"contact": None})
    assert cleared.json()["contact"] is None
    assert cleared.json()["createdAt"] == data["createdAt"]
    assert client.get("/api/v1/farms?page=2&pageSize=1", headers=HEADERS).json()["total"] == 2
    assert client.get("/api/v1/farms?page=3&pageSize=1", headers=HEADERS).json()["items"] == []
    assert client.delete(f'/api/v1/farms/{data["id"]}', headers=HEADERS).content == b""
    assert client.get(f'/api/v1/farms/{data["id"]}', headers=HEADERS).status_code == 404
    assert len(farm.JsonStore().rows) == 1


def test_auth_and_owner_isolation(setup, monkeypatch):
    client, _, identity = setup
    assert client.get("/api/v1/farms").status_code == 401
    identity.owner = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    assert client.get("/api/v1/farms", headers=HEADERS).json()["items"] == []
    for method, payload in [("get", None), ("patch", {"notes": "foreign"}), ("delete", None)]:
        kwargs = {"headers": HEADERS}
        if payload:
            kwargs["json"] = payload
        assert getattr(client, method)(f"/api/v1/farms/{ID}", **kwargs).status_code == 404
    identity.account = "guest"
    monkeypatch.setattr(gateway, "GUEST_ENABLED_MODULES", {"farms"})
    assert client.get("/api/v1/farms", headers=HEADERS).status_code == 403


@pytest.mark.parametrize("payload", [{}, {"name": " "}, {"name": None}, {"boundary": {"type": "Polygon", "coordinates": []}}, {"fields": []}, {"contact": {"ownerName": "X", "email": "invalid"}}, {"summary": {}}])
def test_invalid_patch(setup, payload):
    client, _, _ = setup
    response = client.patch(f"/api/v1/farms/{ID}", headers=HEADERS, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_legacy_put_and_summary(setup):
    client, _, _ = setup
    response = client.put(f"/api/v1/farms/{ID}", headers=HEADERS, json={"farmName": "Legacy", "fields": [{"id": "legacy", "areaM2": 123}], "template": {"items": ["kept"]}})
    assert response.status_code == 200
    assert response.json()["summary"]["fieldAreaM2"] == 123
    assert client.patch(f"/api/v1/farms/{ID}", headers=HEADERS, json={"notes": "only notes"}).json()["summary"]["fieldCount"] == 1
    assert client.get("/api/v1/farms?page=0", headers=HEADERS).status_code == 422
    assert client.get("/api/v1/farms?pageSize=101", headers=HEADERS).status_code == 422


def test_configuration(monkeypatch):
    monkeypatch.delenv("FARM_STORAGE_BACKEND", raising=False)
    assert farm.storage_backend() == "postgres"
    monkeypatch.setenv("FARM_STORAGE_BACKEND", "json")
    monkeypatch.setenv("APP_ENV", "development")
    assert farm.storage_backend() == "json"
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        farm.storage_backend()


def test_service_rejects_invalid_data(setup):
    _, service, _ = setup
    from farm.v1 import farm_pb2
    with pytest.raises(Error) as error:
        asyncio.run(service.CreateFarm(farm_pb2.FarmRequest(owner_id=OWNER, data_json=json.dumps({"name": "X", "boundary": {"type": "Polygon"}})), Context()))
    assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
