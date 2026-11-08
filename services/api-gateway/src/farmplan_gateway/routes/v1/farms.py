"""Farm-only HTTP contracts. Identity always comes from the verified token."""
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.concurrency import run_in_threadpool


class Contact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ownerName: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        import re
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Invalid email")
        return value


class FarmCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    location: str = Field(default="", max_length=200)
    climateZone: str = Field(default="", max_length=120)
    boundary: None = None
    notes: str = Field(default="", max_length=5000)
    contact: Contact | None = None

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Name must not be blank")
        return value.strip()


class FarmPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=200)
    climateZone: str | None = Field(default=None, max_length=120)
    boundary: None = None
    notes: str | None = Field(default=None, max_length=5000)
    contact: Contact | None = None

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set:
            raise ValueError("Empty patch")
        for key in self.model_fields_set - {"boundary", "contact"}:
            if getattr(self, key) is None:
                raise ValueError("Text cannot be null")
        if self.name is not None and not self.name.strip():
            raise ValueError("Name must not be blank")
        return self


class Summary(BaseModel):
    fieldCount: int
    fieldAreaM2: float | None
    activePlanCount: int | None


class FarmResponse(FarmCreate):
    id: UUID
    createdAt: datetime
    updatedAt: datetime
    boundaryAreaM2: float | None
    boundaryPerimeterM: float | None
    summary: Summary


class FarmList(BaseModel):
    items: list[FarmResponse]
    total: int
    page: int
    pageSize: int


def register(app, deps):
    def authorize(user):
        deps.require_module("farms", user.account_type)
        # Farm persistence is never available to guests, even if module flags change.
        if user.account_type == "guest":
            raise HTTPException(403)

    async def call(method, request):
        try:
            return await run_in_threadpool(getattr(deps.farm_client, method), request, timeout=10)
        except deps.grpc.RpcError as error:
            if error.code() == deps.grpc.StatusCode.INVALID_ARGUMENT:
                raise HTTPException(422) from error
            deps.raise_http_error(error)

    async def list_farms(page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), user: Any = Depends(deps.current_user)):
        authorize(user)
        result = await call("ListFarms", deps.farm_pb2.ListFarmsRequest(owner_id=user.user_id, page=page, page_size=pageSize))
        return dict(items=[deps.farm_from_proto(f) for f in result.farms], total=result.total, page=page, pageSize=pageSize)

    async def create_farm(request: FarmCreate | deps.FarmCreateRequest, user: Any = Depends(deps.current_user)):
        authorize(user)
        data = request.model_dump(mode="json", exclude={"createdAt"})
        result = await call("CreateFarm", deps.farm_pb2.FarmRequest(owner_id=user.user_id, data_json=json.dumps(data)))
        return deps.farm_from_proto(result.farm)

    async def get_farm(farm_id: UUID, user: Any = Depends(deps.current_user)):
        authorize(user)
        result = await call("GetFarm", deps.farm_pb2.FarmIdRequest(owner_id=user.user_id, farm_id=str(farm_id)))
        return deps.farm_from_proto(result.farm)

    async def patch_farm(farm_id: UUID, request: FarmPatch, user: Any = Depends(deps.current_user)):
        authorize(user)
        return await update(farm_id, request, user)

    async def update(farm_id, request, user):
        data = request.model_dump(mode="json", exclude_unset=True, exclude={"createdAt"})
        result = await call("UpdateFarm", deps.farm_pb2.UpdateFarmRequest(owner_id=user.user_id, farm_id=str(farm_id), data_json=json.dumps(data)))
        return deps.farm_from_proto(result.farm)

    async def legacy_put(farm_id: UUID, request: deps.FarmUpdateRequest, user: Any = Depends(deps.current_user)):
        authorize(user)
        return await update(farm_id, request, user)

    async def delete_farm(farm_id: UUID, user: Any = Depends(deps.current_user)):
        authorize(user)
        await call("DeleteFarm", deps.farm_pb2.FarmIdRequest(owner_id=user.user_id, farm_id=str(farm_id)))
        return Response(status_code=204)

    base = "/api/v1/farms"
    app.add_api_route(base, list_farms, methods=["GET"], response_model=FarmList, tags=["farms"])
    app.add_api_route(base, create_farm, methods=["POST"], status_code=201, response_model=FarmResponse, tags=["farms"])
    for method, handler in [("GET", get_farm), ("PATCH", patch_farm), ("PUT", legacy_put)]:
        app.add_api_route(base + "/{farm_id}", handler, methods=[method], response_model=FarmResponse, tags=["farms"], deprecated=method == "PUT")
    app.add_api_route(base + "/{farm_id}", delete_farm, methods=["DELETE"], status_code=204, tags=["farms"])
