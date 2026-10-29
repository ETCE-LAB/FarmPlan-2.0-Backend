import grpc
from fastapi.testclient import TestClient

from farmplan_gateway import main as gateway
from identity.v1 import identity_pb2


class FakeIdentityClient:
    def Register(self, request, timeout=None):
        self.register_request = request
        return identity_pb2.AuthResponse(
            access_token="user-token",
            token_type="Bearer",
            user_id="registered-user",
            account_type="user",
        )

    def Login(self, request, timeout=None):
        self.login_request = request
        return identity_pb2.AuthResponse(
            access_token="user-token",
            token_type="Bearer",
            user_id="registered-user",
            account_type="user",
        )

    def CreateGuestSession(self, request, timeout=None):
        return identity_pb2.AuthResponse(
            access_token="guest-token",
            token_type="Bearer",
            user_id="anonymous-session",
            account_type="guest",
        )

    def GetUser(self, request, timeout=None):
        if request.access_token == "guest-token":
            return identity_pb2.UserProfile(
                user_id="anonymous-session", display_name="Guest", account_type="guest"
            )
        return identity_pb2.UserProfile(
            user_id="registered-user",
            email="grower@example.test",
            display_name="Test Grower",
            account_type="user",
        )


def test_health_endpoint():
    response = TestClient(gateway.app).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api-gateway"}


def test_register_forwards_credentials_to_identity_service(monkeypatch):
    fake_identity = FakeIdentityClient()
    monkeypatch.setattr(gateway, "identity_client", fake_identity)

    response = TestClient(gateway.app).post(
        "/api/v1/auth/register",
        json={
            "email": "grower@example.test",
            "password": "a-long-test-password",
            "display_name": "Test Grower",
        },
    )

    assert response.status_code == 201
    assert response.json()["account_type"] == "user"
    assert fake_identity.register_request.email == "grower@example.test"


def test_login_forwards_credentials_to_identity_service(monkeypatch):
    fake_identity = FakeIdentityClient()
    monkeypatch.setattr(gateway, "identity_client", fake_identity)

    response = TestClient(gateway.app).post(
        "/api/v1/auth/login",
        json={"email": "grower@example.test", "password": "long-test-password"},
    )

    assert response.status_code == 200
    assert response.json()["account_type"] == "user"
    assert fake_identity.login_request.email == "grower@example.test"


def test_invalid_login_is_translated_to_http_401(monkeypatch):
    class UnauthenticatedError(grpc.RpcError):
        def code(self):
            return grpc.StatusCode.UNAUTHENTICATED

        def details(self):
            return "Invalid email or password."

    class RejectingIdentityClient:
        def Login(self, request, timeout=None):
            raise UnauthenticatedError()

    monkeypatch.setattr(gateway, "identity_client", RejectingIdentityClient())
    response = TestClient(gateway.app).post(
        "/api/v1/auth/login",
        json={"email": "grower@example.test", "password": "wrong-test-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_register_rejects_short_password_before_grpc_call():
    response = TestClient(gateway.app).post(
        "/api/v1/auth/register",
        json={"email": "grower@example.test", "password": "short", "display_name": "Grower"},
    )
    assert response.status_code == 422


def test_guest_session_can_read_own_profile(monkeypatch):
    monkeypatch.setattr(gateway, "identity_client", FakeIdentityClient())
    client = TestClient(gateway.app)

    session_response = client.post("/api/v1/auth/guest")
    assert session_response.status_code == 200
    assert session_response.json()["account_type"] == "guest"

    profile_response = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer guest-token"}
    )
    assert profile_response.status_code == 200
    assert profile_response.json() == {
        "user_id": "anonymous-session",
        "email": "",
        "display_name": "Guest",
        "account_type": "guest",
    }


def test_protected_endpoint_requires_bearer_token():
    response = TestClient(gateway.app).get("/api/v1/modules")
    assert response.status_code == 401


def test_guest_can_access_enabled_guest_module_but_not_account_only_module(monkeypatch):
    monkeypatch.setattr(gateway, "identity_client", FakeIdentityClient())
    monkeypatch.setattr(gateway, "ENABLED_MODULES", {"catalog", "farms"})
    monkeypatch.setattr(gateway, "GUEST_ENABLED_MODULES", {"catalog"})
    client = TestClient(gateway.app)
    headers = {"Authorization": "Bearer guest-token"}

    assert client.get("/api/v1/modules/catalog/access", headers=headers).status_code == 200
    assert client.get("/api/v1/modules/farms/access", headers=headers).status_code == 403
    assert client.get("/api/v1/modules/planning/access", headers=headers).status_code == 404


def test_registered_user_can_access_enabled_module(monkeypatch):
    monkeypatch.setattr(gateway, "identity_client", FakeIdentityClient())
    monkeypatch.setattr(gateway, "ENABLED_MODULES", {"farms"})

    response = TestClient(gateway.app).get(
        "/api/v1/modules/farms/access", headers={"Authorization": "Bearer user-token"}
    )

    assert response.status_code == 200
    assert response.json()["account_type"] == "user"


def test_module_list_reports_independent_availability_and_guest_access(monkeypatch):
    monkeypatch.setattr(gateway, "identity_client", FakeIdentityClient())
    monkeypatch.setattr(gateway, "ENABLED_MODULES", {"catalog", "farms"})
    monkeypatch.setattr(gateway, "GUEST_ENABLED_MODULES", {"catalog"})

    response = TestClient(gateway.app).get(
        "/api/v1/modules", headers={"Authorization": "Bearer guest-token"}
    )

    assert response.status_code == 200
    modules = {item["id"]: item for item in response.json()["modules"]}
    assert modules["catalog"]["enabled"] is True
    assert modules["catalog"]["accessible"] is True
    assert modules["farms"]["enabled"] is True
    assert modules["farms"]["accessible"] is False
    assert modules["planning"]["enabled"] is False
