"""Owner-scoped Farm service with PostgreSQL and explicit ephemeral development storage."""
import asyncio
from copy import deepcopy
from datetime import UTC, datetime
import json
import math
import os
from pathlib import Path
import re
import uuid

import asyncpg
import grpc
from grpc import aio
from farm.v1 import farm_pb2, farm_pb2_grpc


def storage_backend():
    backend = os.getenv("FARM_STORAGE_BACKEND", "postgres")
    if backend not in {"postgres", "json"}:
        raise RuntimeError("FARM_STORAGE_BACKEND must be postgres or json")
    if backend == "json" and os.getenv("APP_ENV", "development") != "development":
        raise RuntimeError("JSON Farm storage is development-only")
    return backend


async def abort(context, code, message):
    await context.abort(code, message)
    raise AssertionError("abort returned")


def validate(data, create=False):
    if not isinstance(data, dict) or not data:
        raise ValueError("Expected non-empty object")
    allowed = {"name", "farmName", "location", "climateZone", "boundary", "notes", "contact", "ownerName", "contactEmail", "fields", "template"}
    if set(data) - allowed:
        raise ValueError("Unknown or read-only property")
    if create and not (data.get("name") or data.get("farmName")):
        raise ValueError("Name required")
    for key, limit in {"name":120, "farmName":120, "location":200, "notes":5000, "climateZone":120, "ownerName":120}.items():
        if key in data and (not isinstance(data[key], str) or len(data[key]) > limit or (key not in {"notes", "climateZone", "location"} and not data[key].strip())):
            raise ValueError("Invalid text")
    if data.get("boundary") is not None:
        raise ValueError("Boundary geometry is not supported in this increment")
    contact = data.get("contact")
    if contact is not None:
        if not isinstance(contact, dict) or set(contact) != {"ownerName", "email"}:
            raise ValueError("Invalid contact")
        if not isinstance(contact["ownerName"], str) or not 1 <= len(contact["ownerName"].strip()) <= 120:
            raise ValueError("Invalid owner name")
    email = contact["email"] if contact else data.get("contactEmail")
    if email is not None and (not isinstance(email, str) or len(email) > 320 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)):
        raise ValueError("Invalid email")
    if "fields" in data and (not isinstance(data["fields"], list) or len(data["fields"]) > 100 or any(not isinstance(f, dict) or not f for f in data["fields"])):
        raise ValueError("Invalid embedded fields")
    if "template" in data and data["template"] is not None and not isinstance(data["template"], dict):
        raise ValueError("Invalid template")
    return data


def resource(row):
    data = row["data"]
    if isinstance(data, str):
        data = json.loads(data)
    fields = data.get("fields", [])
    areas = [f.get("areaM2") for f in fields]
    known = all(isinstance(a, (int, float)) and not isinstance(a, bool) and math.isfinite(a) and a >= 0 for a in areas)
    contact = data.get("contact")
    if "contact" not in data and data.get("ownerName") and data.get("contactEmail"):
        contact = {"ownerName": data["ownerName"], "email": data["contactEmail"]}
    return dict(id=str(row["id"]), name=data.get("name", data.get("farmName", "")),
        location=data.get("location", ""), climateZone=data.get("climateZone", ""), boundary=None,
        boundaryAreaM2=None, boundaryPerimeterM=None, notes=data.get("notes", ""), contact=contact,
        summary=dict(fieldCount=len(fields), fieldAreaM2=sum(areas) if known else None, activePlanCount=None),
        createdAt=row["created_at"].isoformat(), updatedAt=row["updated_at"].isoformat())


class JsonStore:
    def __init__(self):
        seed = json.loads(Path(__file__).with_name("seed.json").read_text())
        self.rows = {}
        for row in seed:
            row["id"] = uuid.UUID(row["id"])
            row["owner_id"] = uuid.UUID(row["owner_id"])
            for key in ("created_at", "updated_at"):
                row[key] = datetime.fromisoformat(row[key])
            self.rows[row["id"]] = row


class FarmService(farm_pb2_grpc.FarmServiceServicer):
    def __init__(self, pool):
        self.pool = pool

    async def ids(self, request, context):
        try:
            owner = uuid.UUID(request.owner_id)
            farm = uuid.UUID(request.farm_id) if hasattr(request, "farm_id") else None
            return owner, farm
        except (ValueError, TypeError, AttributeError):
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Invalid UUID")

    async def data(self, request, context, create=False):
        try:
            data = validate(json.loads(request.data_json), create)
            # Store contact through existing legacy keys so the PUT adapter and
            # new PATCH contract cannot leave competing contact representations.
            if "contact" in data:
                contact = data.pop("contact")
                data["ownerName"] = contact["ownerName"] if contact else None
                data["contactEmail"] = contact["email"] if contact else None
            if "name" in data:
                data["farmName"] = data["name"]
            return data
        except (ValueError, TypeError):
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Invalid Farm data")

    def record(self, row):
        return farm_pb2.FarmRecord(id=str(row["id"]), data_json=json.dumps(resource(row)))

    async def ListFarms(self, request, context):
        owner, _ = await self.ids(request, context)
        page, size = request.page or 1, request.page_size or 20
        if size > 100:
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Page size exceeds 100")
        if isinstance(self.pool, JsonStore):
            rows = sorted((deepcopy(r) for r in self.pool.rows.values() if r["owner_id"] == owner), key=lambda r: (r["created_at"], str(r["id"])), reverse=True)
        else:
            rows = await self.pool.fetch("SELECT * FROM farms WHERE owner_id=$1 ORDER BY created_at DESC, id DESC", owner)
        return farm_pb2.ListFarmsResponse(farms=[self.record(r) for r in rows[(page-1)*size:page*size]], total=len(rows), page=page, page_size=size)

    async def GetFarm(self, request, context):
        owner, farm = await self.ids(request, context)
        if isinstance(self.pool, JsonStore):
            row = self.pool.rows.get(farm)
            if row and row["owner_id"] != owner:
                row = None
        else:
            row = await self.pool.fetchrow("SELECT * FROM farms WHERE id=$1 AND owner_id=$2", farm, owner)
        if row is None:
            await abort(context, grpc.StatusCode.NOT_FOUND, "Farm not found")
        return farm_pb2.FarmResponse(farm=self.record(row))

    async def CreateFarm(self, request, context):
        owner, _ = await self.ids(request, context)
        data = await self.data(request, context, True)
        farm = uuid.uuid4()
        if isinstance(self.pool, JsonStore):
            now = datetime.now(UTC)
            row = dict(id=farm, owner_id=owner, data=deepcopy(data), created_at=now, updated_at=now)
            self.pool.rows[farm] = row
        else:
            row = await self.pool.fetchrow("INSERT INTO farms(id,owner_id,data) VALUES($1,$2,$3::jsonb) RETURNING *", farm, owner, json.dumps(data))
        return farm_pb2.FarmResponse(farm=self.record(row))

    async def UpdateFarm(self, request, context):
        owner, farm = await self.ids(request, context)
        data = await self.data(request, context)
        # Keep legacy aliases synchronized without replacing embedded fields/templates.
        if "farmName" in data:
            data["name"] = data["farmName"]
        if isinstance(self.pool, JsonStore):
            row = self.pool.rows.get(farm)
            if row and row["owner_id"] == owner:
                row["data"].update(deepcopy(data))
                row["updated_at"] = datetime.now(UTC)
            else:
                row = None
        else:
            row = await self.pool.fetchrow("UPDATE farms SET data=data || $3::jsonb, updated_at=now() WHERE id=$1 AND owner_id=$2 RETURNING *", farm, owner, json.dumps(data))
        if row is None:
            await abort(context, grpc.StatusCode.NOT_FOUND, "Farm not found")
        return farm_pb2.FarmResponse(farm=self.record(row))

    async def DeleteFarm(self, request, context):
        owner, farm = await self.ids(request, context)
        if isinstance(self.pool, JsonStore):
            row = self.pool.rows.get(farm)
            deleted = row is not None and row["owner_id"] == owner
            if deleted:
                del self.pool.rows[farm]
        else:
            deleted = await self.pool.execute("DELETE FROM farms WHERE id=$1 AND owner_id=$2", farm, owner) != "DELETE 0"
        if not deleted:
            await abort(context, grpc.StatusCode.NOT_FOUND, "Farm not found")
        return farm_pb2.DeleteFarmResponse(deleted=True)


async def serve():
    pool = JsonStore() if storage_backend() == "json" else await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=10)
    server = aio.server()
    farm_pb2_grpc.add_FarmServiceServicer_to_server(FarmService(pool), server)
    server.add_insecure_port("[::]:50051")
    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        if not isinstance(pool, JsonStore):
            await pool.close()


if __name__ == "__main__":
    asyncio.run(serve())
