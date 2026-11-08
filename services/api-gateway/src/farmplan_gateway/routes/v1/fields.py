"""Field transport schemas. Farm owns all topology and containment rules."""
from datetime import datetime
import json
from typing import Any, Literal
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, model_validator
from starlette.concurrency import run_in_threadpool

Number = StrictFloat | StrictInt
Position = list[Number]


class Polygon(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["Polygon"]
    coordinates: list[list[Position]] = Field(min_length=1, max_length=100)


class MultiPolygon(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["MultiPolygon"]
    coordinates: list[list[list[Position]]] = Field(min_length=1, max_length=100)


class FieldCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=120)
    geometry: Polygon
    excludedZones: MultiPolygon | None = None
    soilType: str | None = Field(default=None, min_length=1, max_length=120)
    soilPh: Number | None = Field(default=None, ge=0, le=14)
    cropType: str | None = Field(default=None, min_length=1, max_length=120)
    irrigation: Literal["none", "drip", "sprinkler", "flood", "other"] = "none"
    autoSpacing: StrictBool = False


class FieldPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    geometry: Polygon | None = None
    excludedZones: MultiPolygon | None = None
    soilType: str | None = Field(default=None, min_length=1, max_length=120)
    soilPh: Number | None = Field(default=None, ge=0, le=14)
    cropType: str | None = Field(default=None, min_length=1, max_length=120)
    irrigation: Literal["none", "drip", "sprinkler", "flood", "other"] | None = None
    autoSpacing: StrictBool | None = None

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set or any(getattr(self, key) is None for key in self.model_fields_set & {"name", "geometry", "irrigation", "autoSpacing"}):
            raise ValueError("Empty patch or null required property")
        return self


class FieldResponse(FieldCreate):
    id: UUID
    farmId: UUID
    areaM2: float
    netAreaM2: float
    perimeterM: float
    createdAt: datetime
    updatedAt: datetime


class FieldItems(BaseModel):
    items: list[FieldResponse]


class FieldList(FieldItems):
    total: int
    page: int
    pageSize: int


class ItemsImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[FieldCreate] = Field(min_length=1, max_length=100)


class FeatureProperties(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=120)
    excludedZones: MultiPolygon | None = None
    soilType: str | None = Field(default=None, min_length=1, max_length=120)
    soilPh: Number | None = Field(default=None, ge=0, le=14)
    cropType: str | None = Field(default=None, min_length=1, max_length=120)
    irrigation: Literal["none", "drip", "sprinkler", "flood", "other"] = "none"
    autoSpacing: StrictBool = False


class Feature(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["Feature"]
    geometry: Polygon
    properties: FeatureProperties


class FeatureCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["FeatureCollection"]
    features: list[Feature] = Field(min_length=1, max_length=100)


async def call_farm(deps, method, request):
    try:
        return await run_in_threadpool(getattr(deps.farm_client, method), request, timeout=10)
    except deps.grpc.RpcError as error:
        if error.code() == deps.grpc.StatusCode.INVALID_ARGUMENT:
            details = []
            try:
                source = json.loads(error.details()).get("details", [])
                allowed = {"invalid_value", "self_intersecting", "invalid_topology", "outside_farm_boundary", "outside_field"}
                for detail in source:
                    if detail.get("code") in allowed and isinstance(detail.get("path"), str):
                        details.append(dict(path=detail["path"], code=detail["code"], message="Invalid geometry or value."))
            except (ValueError, TypeError, AttributeError):
                pass
            raise HTTPException(422, detail={"validation_details": details}) from error
        deps.raise_http_error(error)


def register(app, deps):
    def authorize(user):
        deps.require_module("farms", user.account_type)
        if user.account_type == "guest":
            raise HTTPException(403)

    async def call(operation, user, farm_id=None, field_id=None, data=None, page=1, size=20):
        authorize(user)
        result = await call_farm(deps, "Fields", deps.farm_pb2.FieldRequest(
            owner_id=user.user_id, farm_id=str(farm_id) if farm_id else "",
            field_id=str(field_id) if field_id else "", operation=operation,
            data_json=json.dumps(data) if data is not None else "", page=page, page_size=size))
        return json.loads(result.data_json)

    async def list_fields(farm_id: UUID, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), user: Any = Depends(deps.current_user)):
        return await call("list", user, farm_id, page=page, size=pageSize)

    async def create_field(farm_id: UUID, request: FieldCreate, user: Any = Depends(deps.current_user)):
        return await call("create", user, farm_id, data=request.model_dump(mode="json"))

    async def bulk_fields(farm_id: UUID, request: ItemsImport | FeatureCollection, user: Any = Depends(deps.current_user)):
        return await call("bulk", user, farm_id, data=request.model_dump(mode="json"))

    async def get_field(field_id: UUID, user: Any = Depends(deps.current_user)):
        return await call("get", user, field_id=field_id)

    async def patch_field(field_id: UUID, request: FieldPatch, user: Any = Depends(deps.current_user)):
        return await call("patch", user, field_id=field_id, data=request.model_dump(mode="json", exclude_unset=True))

    async def delete_field(field_id: UUID, user: Any = Depends(deps.current_user)):
        await call("delete", user, field_id=field_id)
        return Response(status_code=204)

    base = "/api/v1/farms/{farm_id}/fields"
    app.add_api_route(base, list_fields, methods=["GET"], response_model=FieldList, tags=["fields"])
    app.add_api_route(base, create_field, methods=["POST"], status_code=201, response_model=FieldResponse, tags=["fields"])
    app.add_api_route(base + ":bulk", bulk_fields, methods=["POST"], status_code=201, response_model=FieldItems, tags=["fields"])
    for method, handler in [("GET", get_field), ("PATCH", patch_field)]:
        app.add_api_route("/api/v1/fields/{field_id}", handler, methods=[method], response_model=FieldResponse, tags=["fields"])
    app.add_api_route("/api/v1/fields/{field_id}", delete_field, methods=["DELETE"], status_code=204, tags=["fields"])
