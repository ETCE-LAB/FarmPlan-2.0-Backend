"""Overview authentication, policy and dedicated RPC transport contract."""
import grpc
import pytest
from fastapi.testclient import TestClient
from farm.v1 import farm_pb2
from identity.v1 import identity_pb2
from farmplan_gateway import main as gateway

OWNER = "9a62eedd-7c33-4c4b-b9dc-99b4c7b7e8d4"
HEADERS = {"Authorization": "Bearer overview-token"}


class Error(grpc.RpcError):
    def __init__(self, status):
        self.status = status

    def code(self):
        return self.status

    def details(self):
        return "private upstream details"


@pytest.fixture
def setup(monkeypatch):
    calls = []

    class Identity:
        account = "user"
        error = None

        def GetUser(self, request, timeout=None):
            assert request.access_token == "overview-token"
            assert timeout == 5
            if self.error:
                raise Error(self.error)
            return identity_pb2.UserProfile(user_id=OWNER, account_type=self.account)

    class Farm:
        error = None

        def GetOverview(self, request, timeout=None):
            calls.append((request, timeout))
            if self.error:
                raise Error(self.error)
            return farm_pb2.GetOverviewResponse(farm_count=3, field_count=7)

    identity, farm = Identity(), Farm()
    monkeypatch.setattr(gateway, "identity_client", identity)
    monkeypatch.setattr(gateway, "farm_client", farm)
    monkeypatch.setattr(gateway, "ENABLED_MODULES", {"farms"})
    return TestClient(gateway.app), identity, farm, calls


def test_counts_and_verified_owner_only(setup):
    client, _, _, calls = setup
    response = client.get("/api/v1/overview?owner_id=foreign&ownerId=foreign", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"farmCount": 3, "fieldCount": 7}
    assert len(calls) == 1
    request, timeout = calls[0]
    assert isinstance(request, farm_pb2.GetOverviewRequest)
    assert request.owner_id == OWNER
    assert timeout == 10


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic invalid"}])
def test_missing_bearer(setup, headers):
    client, _, _, calls = setup
    assert client.get("/api/v1/overview", headers=headers).status_code == 401
    assert not calls


def test_invalid_token(setup):
    client, identity, _, calls = setup
    identity.error = grpc.StatusCode.UNAUTHENTICATED
    assert client.get("/api/v1/overview", headers=HEADERS).status_code == 401
    assert not calls


def test_guest_denied_even_when_module_allows_guests(setup, monkeypatch):
    client, identity, _, calls = setup
    identity.account = "guest"
    monkeypatch.setattr(gateway, "GUEST_ENABLED_MODULES", {"farms"})
    assert client.get("/api/v1/overview", headers=HEADERS).status_code == 403
    assert not calls


def test_global_overview_independent_of_module_enablement(setup, monkeypatch):
    client, _, _, calls = setup
    monkeypatch.setattr(gateway, "ENABLED_MODULES", set())
    response = client.get("/api/v1/overview", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"farmCount": 3, "fieldCount": 7}
    assert len(calls) == 1


def test_openapi_groups_overview_separately(setup):
    client, _, _, _ = setup
    operation = client.get("/openapi.json").json()["paths"]["/api/v1/overview"]["get"]
    assert operation["tags"] == ["overview"]


@pytest.mark.parametrize("code,status", [(grpc.StatusCode.UNAVAILABLE, 503),
    (grpc.StatusCode.DEADLINE_EXCEEDED, 504), (grpc.StatusCode.INTERNAL, 502),
    (grpc.StatusCode.RESOURCE_EXHAUSTED, 429)])
def test_upstream_errors(setup, code, status):
    client, _, farm, _ = setup
    farm.error = code
    response = client.get("/api/v1/overview", headers=HEADERS)
    assert response.status_code == status
    assert set(response.json()) == {"error"}
    assert "private" not in response.text
