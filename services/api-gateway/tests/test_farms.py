import json

from fastapi.testclient import TestClient

from farmplan_gateway import main as gateway
from farm.v1 import farm_pb2
from identity.v1 import identity_pb2


class FakeIdentityClient:
    def GetUser(self, request, timeout=None):
        return identity_pb2.UserProfile(
            user_id="9a62eedd-7c33-4c4b-b9dc-99b4c7b7e8d4",
            display_name="Test Grower",
            account_type="user",
        )


class FakeFarmClient:
    def CreateFarm(self, request, timeout=None):
        self.create_request = request
        return farm_pb2.FarmResponse(
            farm=farm_pb2.FarmRecord(id="c56c779b-2ee1-4a15-af56-7a3c1c4fb3c8", data_json=request.data_json)
        )

    def UpdateFarm(self, request, timeout=None):
        self.update_request = request
        return farm_pb2.FarmResponse(
            farm=farm_pb2.FarmRecord(id=request.farm_id, data_json=request.data_json)
        )

    def DeleteFarm(self, request, timeout=None):
        self.delete_request = request
        return farm_pb2.DeleteFarmResponse(deleted=True)

    def ListFarms(self, request, timeout=None):
        self.list_request = request
        return farm_pb2.ListFarmsResponse()


VALID_FARM = {
    "farmName": "Sunrise Farm",
    "ownerName": "Test Grower",
    "location": "Braunschweig",
    "contactEmail": "grower@example.test",
}


def configured_client(monkeypatch):
    farms = FakeFarmClient()
    monkeypatch.setattr(gateway, "identity_client", FakeIdentityClient())
    monkeypatch.setattr(gateway, "farm_client", farms)
    return TestClient(gateway.app), farms


def test_create_farm_validates_input_and_assigns_authenticated_owner(monkeypatch):
    client, farms = configured_client(monkeypatch)
    response = client.post("/api/v1/farms", headers={"Authorization": "Bearer token"}, json=VALID_FARM)

    assert response.status_code == 201
    assert response.json()["farm"]["farmName"] == "Sunrise Farm"
    assert farms.create_request.owner_id == "9a62eedd-7c33-4c4b-b9dc-99b4c7b7e8d4"
    assert json.loads(farms.create_request.data_json)["fields"] == []


def test_create_farm_rejects_blank_or_invalid_contact_email(monkeypatch):
    client, _ = configured_client(monkeypatch)
    headers = {"Authorization": "Bearer token"}

    assert client.post("/api/v1/farms", headers=headers, json={}).status_code == 422
    invalid = {**VALID_FARM, "contactEmail": "not-an-email"}
    assert client.post("/api/v1/farms", headers=headers, json=invalid).status_code == 422
    blank = {**VALID_FARM, "farmName": "  "}
    assert client.post("/api/v1/farms", headers=headers, json=blank).status_code == 422


def test_create_farm_rejects_invalid_polygon_coordinates(monkeypatch):
    client, _ = configured_client(monkeypatch)
    invalid = {
        **VALID_FARM,
        "fields": [{"id": "field-1", "borderPolygon": [{"lat": 95, "lng": 10}] * 3}],
    }
    response = client.post(
        "/api/v1/farms", headers={"Authorization": "Bearer token"}, json=invalid
    )
    assert response.status_code == 422


def test_update_rejects_empty_payload_and_unknown_properties(monkeypatch):
    client, _ = configured_client(monkeypatch)
    headers = {"Authorization": "Bearer token"}

    assert client.put("/api/v1/farms/any-id", headers=headers, json={}).status_code == 422
    assert client.put(
        "/api/v1/farms/any-id", headers=headers, json={"unrecognized": "value"}
    ).status_code == 422


def test_farm_endpoints_require_bearer_authentication(monkeypatch):
    client, _ = configured_client(monkeypatch)
    assert client.get("/api/v1/farms").status_code == 401


def test_list_farms_scopes_service_request_to_authenticated_owner(monkeypatch):
    client, farms = configured_client(monkeypatch)

    response = client.get("/api/v1/farms", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert farms.list_request.owner_id == "9a62eedd-7c33-4c4b-b9dc-99b4c7b7e8d4"


def test_guest_cannot_list_or_mutate_farms(monkeypatch):
    class GuestIdentityClient(FakeIdentityClient):
        def GetUser(self, request, timeout=None):
            return identity_pb2.UserProfile(
                user_id="guest-session",
                display_name="Guest",
                account_type="guest",
            )

    farms = FakeFarmClient()
    monkeypatch.setattr(gateway, "identity_client", GuestIdentityClient())
    monkeypatch.setattr(gateway, "farm_client", farms)
    client = TestClient(gateway.app)
    headers = {"Authorization": "Bearer token"}

    assert client.get("/api/v1/farms", headers=headers).status_code == 403
    assert client.post("/api/v1/farms", headers=headers, json=VALID_FARM).status_code == 403
    assert not hasattr(farms, "list_request")
    assert not hasattr(farms, "create_request")
