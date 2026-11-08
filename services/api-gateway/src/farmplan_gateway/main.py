"""Public FastAPI edge. Internal identity calls use the versioned gRPC contract."""

import json
import math
import os
import re
import sys
from datetime import datetime
from typing import Annotated, NoReturn

import grpc
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from urllib.parse import urlsplit
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.concurrency import run_in_threadpool

from farm.v1 import farm_pb2, farm_pb2_grpc
from identity.v1 import identity_pb2, identity_pb2_grpc

IDENTITY_SERVICE_ADDRESS = os.environ.get("IDENTITY_SERVICE_ADDRESS", "identity-service:50051")
KNOWN_MODULES = {"farms", "catalog", "planning", "analysis", "media"}
ENABLED_MODULES = {
    item.strip().lower()
    for item in os.environ.get("ENABLED_MODULES", "farms,catalog,planning,analysis,media").split(",")
    if item.strip()
}
GUEST_ENABLED_MODULES = {
    item.strip().lower()
    for item in os.environ.get("GUEST_ENABLED_MODULES", "catalog,planning").split(",")
    if item.strip()
}
channel = grpc.insecure_channel(IDENTITY_SERVICE_ADDRESS)
identity_client = identity_pb2_grpc.IdentityServiceStub(channel)
FARM_SERVICE_ADDRESS = os.environ.get("FARM_SERVICE_ADDRESS", "farm-service:50051")
farm_channel = grpc.insecure_channel(FARM_SERVICE_ADDRESS)
farm_client = farm_pb2_grpc.FarmServiceStub(farm_channel)
security = HTTPBearer(auto_error=False)
APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
if APP_ENV not in {"development", "test", "production"}:
    raise RuntimeError("APP_ENV must be development, test, or production.")
class ErrorDetail(BaseModel):
    path: str
    code: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody


class UserResponse(BaseModel):
    id: str
    email: str
    displayName: str
    accountType: str
    createdAt: str
    updatedAt: str


class AuthResponse(BaseModel):
    accessToken: str
    tokenType: str
    expiresIn: int
    user: UserResponse


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    displayName: str = Field(min_length=1, max_length=120)

    @field_validator("displayName")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class PasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    currentPassword: str = Field(min_length=1, max_length=256)
    newPassword: str = Field(min_length=12, max_length=256)


class ModuleResponse(BaseModel):
    id: str
    enabled: bool
    availableToGuest: bool
    accessible: bool


class ModulesResponse(BaseModel):
    modules: list[ModuleResponse]


class ModuleAccessResponse(BaseModel):
    moduleId: str
    accessible: bool
    accountType: str


ERRORS = {
    400: ("invalid_argument", "Invalid request."),
    401: ("unauthenticated", "Authentication required or credentials invalid."),
    403: ("permission_denied", "Permission denied."),
    404: ("not_found", "Resource not found."),
    405: ("method_not_allowed", "Method not allowed."),
    409: ("conflict", "Resource conflict."),
    422: ("validation_failed", "Request validation failed."),
    429: ("rate_limited", "Too many requests."),
    500: ("internal_error", "Internal server error."),
    502: ("upstream_error", "Upstream service request failed."),
    503: ("upstream_unavailable", "Upstream service unavailable."),
    504: ("upstream_timeout", "Upstream service timed out."),
}

app = FastAPI(
    responses={code: {"model": ErrorResponse} for code in ERRORS},
    title="FarmPlan API",
    version="1.0.0",
    docs_url=None if APP_ENV == "production" else "/docs",
    redoc_url=None if APP_ENV == "production" else "/redoc",
    openapi_url=None if APP_ENV == "production" else "/openapi.json",
)


def error_response(status_code, details=None, headers=None):
    code, message = ERRORS.get(status_code, ("http_error", "Request failed."))
    return JSONResponse(status_code=status_code, headers=headers,
        content={"error": {"code": code, "message": message, "details": details or []}})


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request, exc):
    return error_response(exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    return error_response(422, [dict(path=".".join(map(str, error["loc"])),
        code=error["type"], message="Invalid value.") for error in exc.errors()])


@app.exception_handler(grpc.RpcError)
async def grpc_error_handler(request, exc):
    try:
        raise_http_error(exc)
    except HTTPException as error:
        return error_response(error.status_code)


@app.exception_handler(Exception)
async def unexpected_error_handler(request, exc):
    return error_response(500)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=120, validation_alias=AliasChoices("displayName", "display_name"))

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("must be a valid email address")
        return value

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("must be a valid email address")
        return value


class FarmData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    farmName: str = Field(min_length=1, max_length=120)
    ownerName: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=200)
    contactEmail: str = Field(min_length=3, max_length=320)
    notes: str = Field(default="", max_length=5000)
    fields: list[dict[str, object]] = Field(default_factory=list, max_length=100)
    template: dict[str, object] | None = None
    createdAt: datetime | None = None

    @field_validator("farmName", "ownerName", "location", "contactEmail")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("contactEmail")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("must be a valid email address")
        return value.lower()

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: list[dict[str, object]]) -> list[dict[str, object]]:
        if any(not isinstance(field, dict) or not field for field in value):
            raise ValueError("each field must be a non-empty object")
        for field in value:
            polygon = field.get("borderPolygon")
            if polygon is not None:
                if not isinstance(polygon, list) or not 3 <= len(polygon) <= 5000:
                    raise ValueError("borderPolygon must contain between 3 and 5000 points")
                coordinates = []
                for point in polygon:
                    if not isinstance(point, dict):
                        raise ValueError("polygon points must be objects with lat/lng")
                    lat, lng = point.get("lat"), point.get("lng")
                    if (isinstance(lat, bool) or not isinstance(lat, (int, float))
                            or isinstance(lng, bool) or not isinstance(lng, (int, float))
                            or not math.isfinite(lat) or not math.isfinite(lng)
                            or not -90 <= lat <= 90 or not -180 <= lng <= 180):
                        raise ValueError("polygon coordinates are outside valid latitude/longitude ranges")
                    coordinates.append((lat, lng))
                if len(set(coordinates)) < 3:
                    raise ValueError("borderPolygon must contain at least three distinct points")
                twice_area = sum(
                    coordinates[index][1] * coordinates[(index + 1) % len(coordinates)][0]
                    - coordinates[(index + 1) % len(coordinates)][1] * coordinates[index][0]
                    for index in range(len(coordinates))
                )
                if math.isclose(twice_area, 0, abs_tol=1e-10):
                    raise ValueError("borderPolygon must enclose a non-zero area")
        return value


class FarmCreateRequest(FarmData):
    pass


class FarmUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    farmName: str | None = Field(default=None, min_length=1, max_length=120)
    ownerName: str | None = Field(default=None, min_length=1, max_length=120)
    location: str | None = Field(default=None, min_length=1, max_length=200)
    contactEmail: str | None = Field(default=None, min_length=3, max_length=320)
    notes: str | None = Field(default=None, max_length=5000)
    fields: list[dict[str, object]] | None = Field(default=None, max_length=100)
    template: dict[str, object] | None = None
    createdAt: datetime | None = None

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("at least one farm field must be provided")
        for name in ("farmName", "ownerName", "location", "contactEmail", "notes", "fields"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        for name in ("farmName", "ownerName", "location"):
            value = getattr(self, name)
            if value is not None and not value.strip():
                raise ValueError(f"{name} must not be blank")
        if self.contactEmail is not None:
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.contactEmail):
                raise ValueError("contactEmail must be a valid email address")
            self.contactEmail = self.contactEmail.strip().lower()
        if self.fields is not None:
            FarmData.validate_fields(self.fields)
        return self


def raise_http_error(error: grpc.RpcError) -> NoReturn:
    code = error.code()
    mapping = {
        grpc.StatusCode.INVALID_ARGUMENT: status.HTTP_400_BAD_REQUEST,
        grpc.StatusCode.ALREADY_EXISTS: status.HTTP_409_CONFLICT,
        grpc.StatusCode.UNAUTHENTICATED: status.HTTP_401_UNAUTHORIZED,
        grpc.StatusCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        grpc.StatusCode.PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
        grpc.StatusCode.UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
        grpc.StatusCode.DEADLINE_EXCEEDED: 504,
        grpc.StatusCode.RESOURCE_EXHAUSTED: 429,
    }
    raise HTTPException(
        status_code=mapping.get(code, status.HTTP_502_BAD_GATEWAY),
        detail="Service request failed.",
    ) from error


def profile_payload(user):
    return dict(id=user.user_id, email=user.email, displayName=user.display_name,
                accountType=user.account_type, createdAt=user.created_at, updatedAt=user.updated_at)


def auth_payload(response, http_response):
    http_response.headers["Cache-Control"] = "no-store"
    if response.refresh_token:
        http_response.set_cookie("refresh_token", response.refresh_token,
            max_age=response.refresh_expires_in, httponly=True, secure=APP_ENV == "production",
            samesite="strict", path="/api/v1/auth")
    else:
        clear_refresh_cookie(http_response)
    return dict(accessToken=response.access_token, tokenType=response.token_type,
                expiresIn=response.expires_in, user=profile_payload(response.user))


def clear_refresh_cookie(response):
    response.delete_cookie("refresh_token", path="/api/v1/auth", httponly=True,
                           secure=APP_ENV == "production", samesite="strict")
    response.headers["Cache-Control"] = "no-store"


def cookie_origin(request: Request):
    if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
        raise HTTPException(403, "Cross-site request rejected.")
    origin = request.headers.get("origin")
    if origin is not None:
        try:
            parsed = urlsplit(origin)
        except ValueError:
            raise HTTPException(403, "Origin rejected.") from None
        expected = urlsplit(str(request.base_url))
        if (parsed.scheme not in {"http", "https"} or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment
                or (parsed.scheme, parsed.netloc.lower()) != (expected.scheme, expected.netloc.lower())):
            raise HTTPException(403, "Origin rejected.")


async def access_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Bearer access token required.")
    return credentials.credentials


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> identity_pb2.UserProfile:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer access token required.")
    try:
        return await run_in_threadpool(
            identity_client.GetUser,
            identity_pb2.GetUserRequest(access_token=credentials.credentials),
            timeout=5,
        )
    except grpc.RpcError as error:
        raise_http_error(error)


def require_module(module_id: str, account_type: str) -> None:
    if module_id not in KNOWN_MODULES or module_id not in ENABLED_MODULES:
        raise HTTPException(status_code=404, detail="Module is not currently available.")
    if account_type == "guest" and module_id not in GUEST_ENABLED_MODULES:
        raise HTTPException(status_code=403, detail="This module requires an account.")


def farm_from_proto(record: farm_pb2.FarmRecord) -> dict[str, object]:
    return {"id": record.id, **json.loads(record.data_json)}


def raise_farm_http_error(error: grpc.RpcError) -> NoReturn:
    code = error.code()
    mapping = {
        grpc.StatusCode.INVALID_ARGUMENT: status.HTTP_400_BAD_REQUEST,
        grpc.StatusCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        grpc.StatusCode.UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
        grpc.StatusCode.DEADLINE_EXCEEDED: 504,
        grpc.StatusCode.RESOURCE_EXHAUSTED: 429,
    }
    raise HTTPException(
        status_code=mapping.get(code, status.HTTP_502_BAD_GATEWAY),
        detail="Service request failed.",
    ) from error


@app.get("/healthz", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api-gateway"}


from farmplan_gateway.routes.v1 import register_v1_routes

register_v1_routes(app, deps=sys.modules[__name__])
