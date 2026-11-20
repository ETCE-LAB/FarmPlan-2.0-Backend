"""Identity gRPC service: account registration, login and anonymous sessions."""

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import NoReturn
from urllib.parse import urlparse

import asyncpg
import grpc
from grpc import aio
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from identity.v1 import identity_pb2, identity_pb2_grpc

DATABASE_URL = os.environ["DATABASE_URL"]
JWT_SECRET_TEXT = os.environ["JWT_SECRET"]
JWT_SECRET = JWT_SECRET_TEXT.encode("utf-8")
APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
TOKEN_ISSUER = os.environ.get("TOKEN_ISSUER", "farmplan-identity")
DEVELOPMENT_JWT_SECRET = "local-development-only-change-this-secret"
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must contain at leeast 32 bytes.")
if APP_ENV == "production" and JWT_SECRET_TEXT == DEVELOPMENT_JWT_SECRET:
    raise RuntimeError("Production must use a unique JWT_SECRET supplied by the deployment environment.")
if APP_ENV == "production" and urlparse(DATABASE_URL).password == "farmplan-dev-only":
    raise RuntimeError("Production must use a unique PostgreSQL password supplied by the deployment environment.")
if APP_ENV not in {"development", "test", "production"}:
    raise RuntimeError("APP_ENV must be development, test, or production.")


async def abort(context, code: grpc.StatusCode, details: str) -> NoReturn:
    await context.abort(code, details)
    raise AssertionError("gRPC context.abort returned unexpectedly")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def issue_token(user_id: str, account_type: str, token_version: int = 0) -> str:
    try:
        uuid.UUID(user_id)
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("Token subject must be a UUID.") from error
    if account_type not in {"user", "guest"}:
        raise ValueError("Token account type is invalid.")
    now = int(time.time())
    header = _b64encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = _b64encode(
        json.dumps(
            {
                "sub": user_id,
                "ver": token_version,
                "account_type": account_type,
                "iss": TOKEN_ISSUER,
                "iat": now,
                "exp": now + (86400 if account_type == "guest" else 3600),
            },
            separators=(",", ":"),
        ).encode("utf-8")
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = hmac.new(JWT_SECRET, signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64encode(signature)}"


def verify_token(token: str) -> dict[str, object]:
    try:
        if not isinstance(token, str) or len(token) > 8192:
            raise ValueError("Invalid token length")
        header_part, payload, signature = token.split(".")
        header = json.loads(base64.urlsafe_b64decode(header_part + "=" * (-len(header_part) % 4)))
        if not isinstance(header, dict) or header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise ValueError("Unsupported token header")
        signing_input = f"{header_part}.{payload}".encode("ascii")
        expected = _b64encode(hmac.new(JWT_SECRET, signing_input, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if not isinstance(claims, dict):
            raise TypeError("Invalid token claims")
        now = int(time.time())
        issued_at = claims.get("iat")
        expires_at = claims.get("exp")
        if (claims.get("iss") != TOKEN_ISSUER
                or claims.get("account_type") not in {"user", "guest"}
                or not isinstance(issued_at, int) or isinstance(issued_at, bool)
                or not isinstance(expires_at, int) or isinstance(expires_at, bool)
                or issued_at > now + 60 or expires_at <= now or expires_at <= issued_at):
            raise ValueError("Expired or invalid token claims")
        uuid.UUID(str(claims["sub"]))
        return claims
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError, OverflowError, binascii.Error) as error:
        raise ValueError("Invalid access token") from error


def hash_password(password: str, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt, 310_000)
    return f"{_b64encode(actual_salt)}${_b64encode(password_hash)}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        salt_text, hash_text = encoded_hash.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(hash_text + "=" * (-len(hash_text) % 4))
    except (ValueError, TypeError, binascii.Error):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return hmac.compare_digest(actual, expected)


DUMMY_PASSWORD_HASH = hash_password("nonexistent-account-dummy-password")


class IdentityService(identity_pb2_grpc.IdentityServiceServicer):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def Register(self, request, context):
        email = request.email.strip().lower()
        if len(email) > 320 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "A valid email address is required.")
        if not 12 <= len(request.password) <= 256:
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Password must be between 12 and 256 characters.")
        display_name = request.display_name.strip()
        if not display_name or len(display_name) > 120:
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Display name must be between 1 and 120 characters.")
        user_id = str(uuid.uuid4())
        password_hash = await asyncio.to_thread(hash_password, request.password)
        try:
            async with self.pool.acquire() as db:
                async with db.transaction():
                    await db.execute(
                        "INSERT INTO users (id, email, display_name, password_hash) VALUES ($1, $2, $3, $4)",
                        uuid.UUID(user_id), email, display_name, password_hash,
                    )
                    row = await db.fetchrow("SELECT * FROM users WHERE id = $1", uuid.UUID(user_id))
                    response = await self._persist_session(db, row)
        except asyncpg.UniqueViolationError:
            await abort(context, grpc.StatusCode.ALREADY_EXISTS, "An account with this email already exists.")
        return response

    async def Login(self, request, context):
        email = request.email.strip().lower()
        if (not 1 <= len(request.password) <= 256
                or len(email) > 320
                or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)):
            await abort(context, grpc.StatusCode.UNAUTHENTICATED, "Invalid email or password.")
        row = await self.pool.fetchrow(
            "SELECT id, password_hash FROM users WHERE email = $1", email
        )
        encoded_hash = row["password_hash"] if row is not None else DUMMY_PASSWORD_HASH
        password_matches = await asyncio.to_thread(verify_password, request.password, encoded_hash)
        if row is None or not password_matches:
            await abort(context, grpc.StatusCode.UNAUTHENTICATED, "Invalid email or password.")
        return await self._new_session(str(row["id"]), context, row["password_hash"])

    async def CreateGuestSession(self, request, context):
        return self._auth_response(str(uuid.uuid4()), "guest")

    async def GetUser(self, request, context):
        try:
            claims = verify_token(request.access_token)
        except ValueError:
            await abort(context, grpc.StatusCode.UNAUTHENTICATED, "Invalid or expired access token.")
        user_id = str(claims["sub"])
        account_type = str(claims["account_type"])
        if account_type == "guest":
            return identity_pb2.UserProfile(
                user_id=user_id, display_name="Guest", account_type="guest",
                created_at=datetime.fromtimestamp(claims["iat"], timezone.utc).isoformat().replace("+00:00", "Z"),
                updated_at=datetime.fromtimestamp(claims["iat"], timezone.utc).isoformat().replace("+00:00", "Z")
            )
        row = await self._authenticated(request.access_token, context)
        return self._profile(row)

    @staticmethod
    def _profile(row):
        return identity_pb2.UserProfile(
            user_id=str(row["id"]), email=row["email"],
            display_name=row["display_name"], account_type="user",
            created_at=row["created_at"].isoformat().replace("+00:00", "Z"),
            updated_at=row["updated_at"].isoformat().replace("+00:00", "Z"),
        )

    async def _authenticated(self, token, context, connection=None):
        try:
            claims = verify_token(token)
        except ValueError:
            await abort(context, grpc.StatusCode.UNAUTHENTICATED, "Invalid or expired access token.")
        if claims["account_type"] != "user":
            await abort(context, grpc.StatusCode.PERMISSION_DENIED, "A registered account is required.")
        db = connection if connection is not None else self.pool
        row = await db.fetchrow("SELECT * FROM users WHERE id = $1" +
                                (" FOR UPDATE" if connection is not None else ""), uuid.UUID(claims["sub"]))
        if row is None or claims.get("ver", 0) != row["token_version"]:
            await abort(context, grpc.StatusCode.UNAUTHENTICATED, "Invalid or expired access token.")
        return row

    async def _new_session(self, user_id, context, password_hash=None):
        async with self.pool.acquire() as db:
            async with db.transaction():
                row = await db.fetchrow("SELECT * FROM users WHERE id = $1 FOR UPDATE", uuid.UUID(user_id))
                if row is None or (password_hash is not None and row["password_hash"] != password_hash):
                    await abort(context, grpc.StatusCode.UNAUTHENTICATED, "Account credentials changed.")
                return await self._persist_session(db, row)

    async def _persist_session(self, db, row):
        refresh = secrets.token_urlsafe(48)
        await db.execute("INSERT INTO identity_refresh_tokens (token_hash, user_id, expires_at) "
                         "VALUES ($1, $2, now() + interval '30 days')",
                         hashlib.sha256(refresh.encode()).hexdigest(), row["id"])
        return identity_pb2.AuthResponse(
            access_token=issue_token(str(row["id"]), "user", row["token_version"]),
            token_type="Bearer", user_id=str(row["id"]), account_type="user",
            expires_in=3600, user=self._profile(row), refresh_token=refresh,
            refresh_expires_in=30 * 86400,
        )

    @staticmethod
    def _refresh_hash(token):
        if not 32 <= len(token) <= 256:
            return ""
        return hashlib.sha256(token.encode()).hexdigest()

    async def Refresh(self, request, context):
        token_hash = self._refresh_hash(request.refresh_token)
        async with self.pool.acquire() as db:
            async with db.transaction():
                # Lock the user before consuming the token, matching password/delete lock order.
                row = await db.fetchrow(
                    "SELECT u.* FROM users u JOIN identity_refresh_tokens r ON r.user_id = u.id "
                    "WHERE r.token_hash = $1 AND r.expires_at > now() FOR UPDATE OF u", token_hash)
                if row is None:
                    await abort(context, grpc.StatusCode.UNAUTHENTICATED, "Invalid or expired refresh token.")
                consumed = await db.fetchrow(
                    "DELETE FROM identity_refresh_tokens WHERE token_hash = $1 AND expires_at > now() RETURNING user_id", token_hash)
                if consumed is None:
                    await abort(context, grpc.StatusCode.UNAUTHENTICATED, "Invalid or expired refresh token.")
                return await self._persist_session(db, row)

    async def Logout(self, request, context):
        await self.pool.execute("DELETE FROM identity_refresh_tokens WHERE token_hash = $1",
                                self._refresh_hash(request.refresh_token))
        return identity_pb2.EmptyResponse()

    async def UpdateProfile(self, request, context):
        if request.HasField("display_name") and not 1 <= len(request.display_name.strip()) <= 120:
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Display name must be between 1 and 120 characters.")
        async with self.pool.acquire() as db:
            async with db.transaction():
                row = await self._authenticated(request.access_token, context, db)
                if request.HasField("display_name"):
                    row = await db.fetchrow("UPDATE users SET display_name = $2, updated_at = now() WHERE id = $1 RETURNING *",
                                            row["id"], request.display_name.strip())
                return self._profile(row)

    async def ChangePassword(self, request, context):
        if not 12 <= len(request.new_password) <= 256 or not 1 <= len(request.current_password) <= 256:
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Invalid password length.")
        new_hash = await asyncio.to_thread(hash_password, request.new_password)
        async with self.pool.acquire() as db:
            async with db.transaction():
                row = await self._authenticated(request.access_token, context, db)
                if not await asyncio.to_thread(verify_password, request.current_password, row["password_hash"]):
                    await abort(context, grpc.StatusCode.UNAUTHENTICATED, "Invalid current password.")
                await db.execute("UPDATE users SET password_hash = $2, token_version = token_version + 1, updated_at = now() WHERE id = $1", row["id"], new_hash)
                await db.execute("DELETE FROM identity_refresh_tokens WHERE user_id = $1", row["id"])
        return identity_pb2.EmptyResponse()

    async def DeleteSelf(self, request, context):
        async with self.pool.acquire() as db:
            async with db.transaction():
                row = await self._authenticated(request.access_token, context, db)
                await db.execute("DELETE FROM users WHERE id = $1", row["id"])
        return identity_pb2.EmptyResponse()

    @staticmethod
    def _auth_response(user_id: str, account_type: str):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return identity_pb2.AuthResponse(
            access_token=issue_token(user_id, account_type), token_type="Bearer",
            user_id=user_id, account_type=account_type, expires_in=86400,
            user=identity_pb2.UserProfile(user_id=user_id, display_name="Guest",
                                          account_type="guest", created_at=now, updated_at=now),
        )


async def serve() -> None:
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

    server = aio.server()
    identity_pb2_grpc.add_IdentityServiceServicer_to_server(IdentityService(pool), server)
    health_servicer = health.aio.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    await health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    server.add_insecure_port("[::]:50051")
    await server.start()
    print(json.dumps({"service": "identity-service", "event": "started", "port": 50051}), flush=True)
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        await pool.close()


if __name__ == "__main__":
    asyncio.run(serve())
