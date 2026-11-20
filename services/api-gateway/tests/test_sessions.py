import grpc
import pytest
from fastapi.testclient import TestClient

from farmplan_gateway import main as gateway
from identity.v1 import identity_pb2 as pb


class Identity:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(request, timeout=None):
            assert timeout == 10
            self.calls.append((name, request))
            user = pb.UserProfile(user_id="user-id", email="grower@example.test",
                display_name="Grower", account_type="user",
                created_at="2026-11-08T00:00:00Z", updated_at="2026-11-08T00:00:00Z")
            if name in {"Login", "Register", "Refresh", "CreateGuestSession"}:
                return pb.AuthResponse(access_token="access", token_type="Bearer", expires_in=900,
                    user=user, refresh_token="refresh-secret", refresh_expires_in=3600)
            if name == "UpdateProfile":
                user.display_name = request.display_name
                return user
            return pb.EmptyResponse()
        return call


@pytest.fixture
def setup(monkeypatch):
    identity = Identity()
    monkeypatch.setattr(gateway, "identity_client", identity)
    return TestClient(gateway.app), identity


def test_login_refresh_logout_cookie_lifecycle(setup, monkeypatch):
    client, identity = setup
    monkeypatch.setattr(gateway, "APP_ENV", "production")
    client = TestClient(gateway.app, base_url="https://testserver")
    response = client.post("/api/v1/auth/login", json={"email": "a@example.test", "password": "password"})
    assert set(response.json()) == {"accessToken", "tokenType", "expiresIn", "user"}
    assert set(response.json()["user"]) == {"id", "email", "displayName", "accountType", "createdAt", "updatedAt"}
    assert "refresh-secret" not in response.text
    cookie = response.headers["set-cookie"]
    for attribute in ("HttpOnly", "Secure", "SameSite=strict", "Path=/api/v1/auth", "Max-Age=3600"):
        assert attribute in cookie
    assert response.headers["cache-control"] == "no-store"
    response = client.post("/api/v1/auth/refresh", headers={"Origin": "https://testserver"})
    assert response.status_code == 200
    assert identity.calls[-1][1].refresh_token == "refresh-secret"
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204 and response.content == b""
    assert identity.calls[-1][0] == "Logout"
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.post("/api/v1/auth/refresh").status_code == 401


@pytest.mark.parametrize("path", ["refresh", "logout", "guest", "login", "register"])
@pytest.mark.parametrize("headers", [
    {"Origin": "https://evil.test"}, {"Origin": "null"},
    {"Origin": "http://testserver.evil.test"},
    {"Origin": "http://testserver", "Sec-Fetch-Site": "cross-site"},
])
def test_cookie_csrf_rejected_before_upstream(setup, path, headers):
    client, identity = setup
    response = client.post("/api/v1/auth/" + path, headers=headers, json={})
    assert response.status_code == 403
    assert identity.calls == []


@pytest.mark.parametrize("name", ["displayName", "display_name"])
def test_register_aliases(setup, name):
    client, identity = setup
    response = client.post("/api/v1/auth/register", json={"email": "a@example.test",
        "password": "a-long-password", name: "Grower"})
    assert response.status_code == 201
    assert identity.calls[-1][1].display_name == "Grower"
    assert "display_name" not in response.text


def test_user_mutations_forward_only_bearer_identity(setup):
    client, identity = setup
    headers = {"Authorization": "Bearer verified-token"}
    response = client.patch("/api/v1/users/me", headers=headers, json={"displayName": " Updated "})
    assert response.status_code == 200
    assert response.json()["displayName"] == "Updated"
    assert identity.calls[-1][1].access_token == "verified-token"
    assert identity.calls[-1][1].HasField("display_name")
    response = client.post("/api/v1/users/me/password", headers=headers,
        json={"currentPassword": "old", "newPassword": "a-new-long-password"})
    assert response.status_code == 204 and response.content == b""
    assert identity.calls[-1][1].current_password == "old"
    assert client.delete("/api/v1/users/me", headers=headers).status_code == 204
    assert identity.calls[-1][0] == "DeleteSelf"
    assert identity.calls[-1][1].access_token == "verified-token"


@pytest.mark.parametrize("method,path,body", [
    ("patch", "/api/v1/users/me", {}),
    ("patch", "/api/v1/users/me", {"displayName": " "}),
    ("patch", "/api/v1/users/me", {"displayName": None}),
    ("patch", "/api/v1/users/me", {"displayName": "Grower", "userId": "other"}),
    ("post", "/api/v1/users/me/password", {"currentPassword": "secret", "newPassword": "short"}),
])
def test_invalid_mutation_is_sanitized(setup, method, path, body):
    client, identity = setup
    response = client.request(method, path, json=body, headers={"Authorization": "Bearer token"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert response.json()["error"]["details"]
    assert "secret" not in response.text
    assert identity.calls == []


@pytest.mark.parametrize("method,path", [("patch", "/api/v1/users/me"),
    ("post", "/api/v1/users/me/password"), ("delete", "/api/v1/users/me")])
def test_mutations_require_bearer(setup, method, path):
    client, identity = setup
    assert client.request(method, path, json={}).status_code == 401
    assert identity.calls == []


@pytest.mark.parametrize("code,http,stable", [
    (grpc.StatusCode.INVALID_ARGUMENT, 400, "invalid_argument"),
    (grpc.StatusCode.UNAUTHENTICATED, 401, "unauthenticated"),
    (grpc.StatusCode.PERMISSION_DENIED, 403, "permission_denied"),
    (grpc.StatusCode.NOT_FOUND, 404, "not_found"),
    (grpc.StatusCode.ALREADY_EXISTS, 409, "conflict"),
    (grpc.StatusCode.UNAVAILABLE, 503, "upstream_unavailable"),
    (grpc.StatusCode.DEADLINE_EXCEEDED, 504, "upstream_timeout"),
    (grpc.StatusCode.INTERNAL, 502, "upstream_error"),
])
def test_upstream_errors_are_sanitized(monkeypatch, code, http, stable):
    class Failure(grpc.RpcError):
        def code(self):
            return code

        def details(self):
            return "password=secret refresh_token=secret database payload"

    class FailingIdentity:
        def Refresh(self, request, timeout=None):
            raise Failure()

    monkeypatch.setattr(gateway, "identity_client", FailingIdentity())
    client = TestClient(gateway.app)
    client.cookies.set("refresh_token", "test")
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == http
    assert response.json()["error"]["code"] == stable
    assert "secret" not in response.text


def test_global_http_validation_and_openapi():
    client = TestClient(gateway.app)
    assert client.get("/missing").json()["error"]["code"] == "not_found"
    assert client.get("/api/v1/auth/login").json()["error"]["code"] == "method_not_allowed"
    invalid = client.post("/api/v1/auth/login", content='{"password":"secret",', headers={"Content-Type": "application/json"})
    assert invalid.status_code == 422 and "secret" not in invalid.text
    schema = client.get("/openapi.json").json()
    for path, method, model in [("/api/v1/auth/login", "post", "AuthResponse"),
        ("/api/v1/auth/refresh", "post", "AuthResponse"),
        ("/api/v1/users/me", "get", "UserResponse"),
        ("/api/v1/users/me", "patch", "UserResponse"),
        ("/api/v1/modules", "get", "ModulesResponse")]:
        responses = schema["paths"][path][method]["responses"]
        assert responses["200"]["content"]["application/json"]["schema"]["$ref"].endswith(model)
        assert responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith("ErrorResponse")
    for path, method in [("/api/v1/auth/logout", "post"), ("/api/v1/users/me", "delete"),
        ("/api/v1/users/me/password", "post")]:
        assert "content" not in schema["paths"][path][method]["responses"]["204"]


@pytest.mark.parametrize("method,path,body", [
    ("post", "/api/v1/auth/register", {"email": "a@example.test", "password": "a-long-password", "displayName": "Grower"}),
    ("post", "/api/v1/auth/login", {"email": "a@example.test", "password": "password"}),
    ("post", "/api/v1/auth/guest", None),
    ("post", "/api/v1/auth/logout", None),
    ("patch", "/api/v1/users/me", {"displayName": "Grower"}),
    ("post", "/api/v1/users/me/password", {"currentPassword": "old", "newPassword": "a-long-password"}),
    ("delete", "/api/v1/users/me", None),
])
def test_every_new_rpc_maps_upstream_failure(monkeypatch, method, path, body):
    class Failure(grpc.RpcError):
        def code(self):
            return grpc.StatusCode.PERMISSION_DENIED

        def details(self):
            return "private upstream payload"

    class FailingIdentity:
        def __getattr__(self, name):
            def call(request, timeout=None):
                raise Failure()
            return call

    monkeypatch.setattr(gateway, "identity_client", FailingIdentity())
    client = TestClient(gateway.app)
    client.cookies.set("refresh_token", "test")
    response = client.request(method, path, json=body, headers={"Authorization": "Bearer token"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
    assert "private" not in response.text


def test_unexpected_error_is_sanitized(monkeypatch):
    class BrokenIdentity:
        def CreateGuestSession(self, request, timeout=None):
            raise RuntimeError("database password=secret")

    monkeypatch.setattr(gateway, "identity_client", BrokenIdentity())
    response = TestClient(gateway.app, raise_server_exceptions=False).post("/api/v1/auth/guest")
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "Internal server error.", "details": []}}


def test_malformed_origin_rejected(setup):
    client, identity = setup
    assert client.post("/api/v1/auth/logout", headers={"Origin": "http://["}).status_code == 403
    assert identity.calls == []


def test_farm_upstream_error_uses_global_envelope(monkeypatch):
    class Failure(grpc.RpcError):
        def code(self):
            return grpc.StatusCode.UNAVAILABLE

        def details(self):
            return "private database connection string"

    class Farm:
        def ListFarms(self, request, timeout=None):
            raise Failure()

    async def user():
        return pb.UserProfile(user_id="owner", account_type="user")

    monkeypatch.setattr(gateway, "farm_client", Farm())
    gateway.app.dependency_overrides[gateway.current_user] = user
    try:
        response = TestClient(gateway.app).get("/api/v1/farms")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "upstream_unavailable"
        assert "private" not in response.text
    finally:
        gateway.app.dependency_overrides.pop(gateway.current_user)
