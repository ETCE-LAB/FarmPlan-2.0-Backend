"""Independent Fields owned and authorized by Farm; atomic JSON/SQL operations."""
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, datetime
import json
import uuid

import grpc
from farm.v1 import farm_pb2
from .geometry import Invalid, bulk_items, field_data


class Fields:
    @asynccontextmanager
    async def field_transaction(self):
        if hasattr(self.pool, "rows"):
            async with self.pool.lock:
                yield None
        else:
            async with self.pool.acquire() as connection:
                async with connection.transaction():
                    yield connection

    async def field_parent(self, connection, farm, owner, context):
        if connection is None:
            row = self.pool.rows.get(farm)
            row = row if row and row["owner_id"] == owner else None
        else:
            row = await connection.fetchrow("SELECT * FROM farms WHERE id=$1 AND owner_id=$2 FOR UPDATE", farm, owner)
        if row is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Farm not found")
        data = row["data"]
        return json.loads(data) if isinstance(data, str) else data

    async def field_error(self, context, error):
        await context.abort(grpc.StatusCode.INVALID_ARGUMENT, json.dumps({"details": error.details}))

    async def Fields(self, request, context):
        # A trusted internal caller supplies owner_id from verified Identity, never HTTP input.
        try:
            owner = uuid.UUID(request.owner_id)
            farm = uuid.UUID(request.farm_id) if request.farm_id else None
            field_id = uuid.UUID(request.field_id) if request.field_id else None
        except ValueError:
            return await self.field_error(context, Invalid("id"))
        operation = request.operation
        if operation not in {"list", "create", "bulk", "get", "patch", "delete"}:
            return await self.field_error(context, Invalid("operation"))
        if (operation in {"list", "create", "bulk"} and (farm is None or field_id is not None)) or (operation in {"get", "patch", "delete"} and field_id is None):
            return await self.field_error(context, Invalid("id"))
        try:
            async with self.field_transaction() as connection:
                existing = None
                if field_id:
                    if connection is None:
                        existing = self.pool.fields.get(field_id)
                    else:
                        row = await connection.fetchrow("SELECT data FROM fields WHERE id=$1", field_id)
                        if row:
                            existing = row["data"]
                            existing = json.loads(existing) if isinstance(existing, str) else existing
                    if existing is None:
                        await context.abort(grpc.StatusCode.NOT_FOUND, "Field not found")
                    farm = uuid.UUID(existing["farmId"])
                parent = await self.field_parent(connection, farm, owner, context)
                # Parent lock serializes all Field writes and boundary changes.
                if connection is not None and field_id:
                    row = await connection.fetchrow("SELECT data FROM fields WHERE id=$1", field_id)
                    if row is None:
                        await context.abort(grpc.StatusCode.NOT_FOUND, "Field not found")
                    existing = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
                if operation == "list":
                    page, size = request.page or 1, request.page_size or 20
                    if size > 100:
                        raise Invalid("pageSize")
                    if connection is None:
                        items = [deepcopy(f) for f in self.pool.fields.values() if f["farmId"] == str(farm)]
                    else:
                        rows = await connection.fetch("SELECT data FROM fields WHERE farm_id=$1", farm)
                        items = [json.loads(r["data"]) if isinstance(r["data"], str) else r["data"] for r in rows]
                    items.sort(key=lambda f: (f["createdAt"], f["id"]))
                    result = dict(items=items[(page-1)*size:page*size], total=len(items), page=page, pageSize=size)
                elif operation == "get":
                    result = existing
                elif operation == "delete":
                    if connection is None:
                        del self.pool.fields[field_id]
                    else:
                        await connection.execute("DELETE FROM fields WHERE id=$1", field_id)
                    result = {}
                else:
                    if len(request.data_json) > 2_000_000:
                        raise Invalid("body", message="Document exceeds 2 MB.")
                    try:
                        document = json.loads(request.data_json)
                    except (ValueError, TypeError):
                        raise Invalid("body") from None
                    if operation == "patch":
                        writable = {k: v for k, v in existing.items() if k not in {"id", "farmId", "createdAt", "updatedAt", "areaM2", "netAreaM2", "perimeterM"}}
                        if not isinstance(document, dict) or not document or set(document) - set(writable):
                            raise Invalid("body")
                        documents = [dict(writable, **document)]
                    else:
                        documents = bulk_items(document) if operation == "bulk" else [document]
                    now = datetime.now(UTC).isoformat()
                    items = []
                    for index, doc in enumerate(documents):
                        try:
                            item = field_data(doc, parent.get("boundary"))
                        except Invalid as error:
                            if operation == "bulk":
                                for detail in error.details:
                                    detail["path"] = f"items.{index}." + detail["path"]
                            raise
                        item.update(id=str(field_id or uuid.uuid4()), farmId=str(farm), createdAt=existing["createdAt"] if existing else now, updatedAt=now)
                        items.append(item)
                    # Validate the entire batch before any mutation.
                    for item in items:
                        key = uuid.UUID(item["id"])
                        if connection is None:
                            self.pool.fields[key] = deepcopy(item)
                        elif operation == "patch":
                            await connection.execute("UPDATE fields SET data=$2::jsonb WHERE id=$1", key, json.dumps(item))
                        else:
                            await connection.execute("INSERT INTO fields(id,farm_id,data) VALUES($1,$2,$3::jsonb)", key, farm, json.dumps(item))
                    result = {"items": items} if operation == "bulk" else items[0]
                return farm_pb2.FieldResult(data_json=json.dumps(result))
        except Invalid as error:
            return await self.field_error(context, error)
