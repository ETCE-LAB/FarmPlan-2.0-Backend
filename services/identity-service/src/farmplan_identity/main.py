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
from typing import NoReturn
from urllib.parse import urlparse

import asyncpg
import grpc
from grpc import aio

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


def issue_token(user_id: str, account_type: str) -> str:
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
            await self.pool.execute(
                "INSERT INTO users (id, email, display_name, password_hash) VALUES ($1, $2, $3, $4)",
                uuid.UUID(user_id),
                email,
                display_name,
                password_hash,
            )
        except asyncpg.UniqueViolationError:
            await abort(context, grpc.StatusCode.ALREADY_EXISTS, "An account with this email already exists.")
        return self._auth_response(user_id, "user")

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
        return self._auth_response(str(row["id"]), "user")

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
                user_id=user_id, display_name="Guest", account_type="guest"
            )
        row = await self.pool.fetchrow(
            "SELECT id, email, display_name FROM users WHERE id = $1", uuid.UUID(user_id)
        )
        if row is None:
            await abort(context, grpc.StatusCode.NOT_FOUND, "User account was not found.")
        return identity_pb2.UserProfile(
            user_id=str(row["id"]),
            email=row["email"],
            display_name=row["display_name"],
            account_type="user",
        )

    @staticmethod
    def _auth_response(user_id: str, account_type: str):
        return identity_pb2.AuthResponse(
            access_token=issue_token(user_id, account_type),
            token_type="Bearer",
            user_id=user_id,
            account_type=account_type,
        )


async def serve() -> None:
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

    server = aio.server()
    identity_pb2_grpc.add_IdentityServiceServicer_to_server(IdentityService(pool), server)
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
