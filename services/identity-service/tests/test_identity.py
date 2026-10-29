import uuid

import pytest

from farmplan_identity import main as identity
from identity.v1 import identity_pb2


class RpcAborted(Exception):
    def __init__(self, code, details):
        self.code = code
        self.details = details


class FakeContext:
    async def abort(self, code, details):
        raise RpcAborted(code, details)


class FakePool:
    def __init__(self, row=None, execute_error=None):
        self.row = row
        self.execute_error = execute_error
        self.execute_args = None

    async def execute(self, query, *args):
        self.execute_args = args
        if self.execute_error:
            raise self.execute_error

    async def fetchrow(self, query, *args):
        return self.row


@pytest.mark.asyncio
async def test_registration_normalizes_email_and_persists_only_password_hash():
    pool = FakePool()
    service = identity.IdentityService(pool)

    response = await service.Register(
        identity_pb2.RegisterRequest(
            email="  Grower@Example.Test ",
            password="long-test-password-123",
            display_name="  Test Grower  ",
        ),
        FakeContext(),
    )

    assert pool.execute_args is not None
    user_id, email, display_name, encoded_hash = pool.execute_args
    assert uuid.UUID(response.user_id) == user_id
    assert response.account_type == "user"
    assert email == "grower@example.test"
    assert display_name == "Test Grower"
    assert encoded_hash != "long-test-password-123"
    assert identity.verify_password("long-test-password-123", encoded_hash)


@pytest.mark.asyncio
async def test_registration_rejects_short_password_without_database_write():
    pool = FakePool()
    service = identity.IdentityService(pool)

    with pytest.raises(RpcAborted) as error:
        await service.Register(
            identity_pb2.RegisterRequest(
                email="grower@example.test", password="short", display_name="Grower"
            ),
            FakeContext(),
        )

    assert error.value.code.name == "INVALID_ARGUMENT"
    assert pool.execute_args is None


@pytest.mark.asyncio
async def test_guest_session_is_account_free_and_token_identifies_guest():
    service = identity.IdentityService(FakePool())

    response = await service.CreateGuestSession(identity_pb2.GuestSessionRequest(), FakeContext())
    claims = identity.verify_token(response.access_token)

    assert response.account_type == "guest"
    assert claims["sub"] == response.user_id
    assert claims["account_type"] == "guest"
    assert claims["exp"] - claims["iat"] == 24 * 60 * 60


@pytest.mark.asyncio
async def test_guest_token_resolves_to_profile_without_database_lookup():
    service = identity.IdentityService(FakePool())
    session = await service.CreateGuestSession(identity_pb2.GuestSessionRequest(), FakeContext())

    profile = await service.GetUser(
        identity_pb2.GetUserRequest(access_token=session.access_token), FakeContext()
    )

    assert profile.user_id == session.user_id
    assert profile.display_name == "Guest"
    assert profile.account_type == "guest"
    assert profile.email == ""


def test_token_signature_rejects_tampering():
    token = identity.issue_token(str(uuid.uuid4()), "user")
    header_and_payload = token.rsplit(".", 1)[0]

    with pytest.raises(ValueError, match="Invalid access token"):
        identity.verify_token(f"{header_and_payload}.invalid-signature")


def test_token_issuance_rejects_non_uuid_subjects_and_unknown_account_types():
    with pytest.raises(ValueError, match="subject must be a UUID"):
        identity.issue_token("not-a-user-id", "user")
    with pytest.raises(ValueError, match="account type is invalid"):
        identity.issue_token(str(uuid.uuid4()), "admin")


def test_expired_token_is_rejected(monkeypatch):
    token = identity.issue_token(str(uuid.uuid4()), "user")
    monkeypatch.setattr(identity.time, "time", lambda: 10**12)

    with pytest.raises(ValueError, match="Invalid access token"):
        identity.verify_token(token)


def test_password_hash_uses_salt_and_verifies_password():
    first_hash = identity.hash_password("same-password")
    second_hash = identity.hash_password("same-password")

    assert first_hash != second_hash
    assert identity.verify_password("same-password", first_hash)
    assert not identity.verify_password("wrong-password", first_hash)


@pytest.mark.asyncio
async def test_login_accepts_valid_password_and_rejects_invalid_password():
    user_id = uuid.uuid4()
    row = {
        "id": user_id,
        "password_hash": identity.hash_password("valid-test-password"),
    }
    service = identity.IdentityService(FakePool(row=row))
    response = await service.Login(
        identity_pb2.LoginRequest(email="grower@example.test", password="valid-test-password"),
        FakeContext(),
    )
    assert response.user_id == str(user_id)

    with pytest.raises(RpcAborted) as error:
        await service.Login(
            identity_pb2.LoginRequest(email="grower@example.test", password="wrong-password"),
            FakeContext(),
        )
    assert error.value.code.name == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_unknown_login_uses_dummy_password_hash_before_rejecting(monkeypatch):
    checked_hashes = []
    original_verify = identity.verify_password

    def capture_verify(password, encoded_hash):
        checked_hashes.append(encoded_hash)
        return original_verify(password, encoded_hash)

    monkeypatch.setattr(identity, "verify_password", capture_verify)
    service = identity.IdentityService(FakePool(row=None))

    with pytest.raises(RpcAborted) as error:
        await service.Login(
            identity_pb2.LoginRequest(email="nobody@example.test", password="valid-format-password"),
            FakeContext(),
        )

    assert error.value.code.name == "UNAUTHENTICATED"
    assert checked_hashes == [identity.DUMMY_PASSWORD_HASH]
