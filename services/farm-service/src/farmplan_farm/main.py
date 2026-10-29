"""Farm gRPC service. Farm records are isolated by their authenticated owner."""

import asyncio
import json
import os
import uuid
from typing import NoReturn

import asyncpg
import grpc
from grpc import aio

from farm.v1 import farm_pb2, farm_pb2_grpc

DATABASE_URL = os.environ["DATABASE_URL"]


async def abort(context, code: grpc.StatusCode, message: str) -> NoReturn:
    await context.abort(code, message)
    raise AssertionError("gRPC context.abort returned unexpectedly")


def decode_data(data_json: str) -> dict:
    try:
        data = json.loads(data_json)
    except (TypeError, ValueError) as error:
        raise ValueError from error
    if not isinstance(data, dict):
        raise TypeError
    return data


class FarmService(farm_pb2_grpc.FarmServiceServicer):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @staticmethod
    async def _owner(owner_id: str, context) -> uuid.UUID:
        try:
            return uuid.UUID(owner_id)
        except (ValueError, TypeError, AttributeError):
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Invalid owner id.")

    @staticmethod
    async def _data(data_json: str, context) -> dict:
        try:
            return decode_data(data_json)
        except (ValueError, TypeError):
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Farm data must be a JSON object.")

    @staticmethod
    def _record(row) -> farm_pb2.FarmRecord:
        data = row["data"]
        if isinstance(data, str):
            data = json.loads(data)
        return farm_pb2.FarmRecord(id=str(row["id"]), data_json=json.dumps(data))

    async def ListFarms(self, request, context):
        owner_id = await self._owner(request.owner_id, context)
        rows = await self.pool.fetch(
            "SELECT id, data FROM farms WHERE owner_id = $1 ORDER BY created_at DESC", owner_id
        )
        return farm_pb2.ListFarmsResponse(farms=[self._record(row) for row in rows])

    async def CreateFarm(self, request, context):
        owner_id = await self._owner(request.owner_id, context)
        data = await self._data(request.data_json, context)
        farm_id = uuid.uuid4()
        row = await self.pool.fetchrow(
            "INSERT INTO farms (id, owner_id, data) VALUES ($1, $2, $3::jsonb) RETURNING id, data",
            farm_id, owner_id, json.dumps(data),
        )
        return farm_pb2.FarmResponse(farm=self._record(row))

    async def UpdateFarm(self, request, context):
        owner_id = await self._owner(request.owner_id, context)
        data = await self._data(request.data_json, context)
        try:
            farm_id = uuid.UUID(request.farm_id)
        except (ValueError, TypeError, AttributeError):
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Invalid farm id.")
        row = await self.pool.fetchrow(
            "UPDATE farms SET data = data || $3::jsonb, updated_at = now() "
            "WHERE id = $1 AND owner_id = $2 RETURNING id, data",
            farm_id, owner_id, json.dumps(data),
        )
        if row is None:
            await abort(context, grpc.StatusCode.NOT_FOUND, "Farm not found.")
        return farm_pb2.FarmResponse(farm=self._record(row))

    async def DeleteFarm(self, request, context):
        owner_id = await self._owner(request.owner_id, context)
        try:
            farm_id = uuid.UUID(request.farm_id)
        except (ValueError, TypeError, AttributeError):
            await abort(context, grpc.StatusCode.INVALID_ARGUMENT, "Invalid farm id.")
        result = await self.pool.execute(
            "DELETE FROM farms WHERE id = $1 AND owner_id = $2", farm_id, owner_id
        )
        if result == "DELETE 0":
            await abort(context, grpc.StatusCode.NOT_FOUND, "Farm not found.")
        return farm_pb2.DeleteFarmResponse(deleted=True)


async def serve() -> None:
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    server = aio.server()
    farm_pb2_grpc.add_FarmServiceServicer_to_server(FarmService(pool), server)
    server.add_insecure_port("[::]:50051")
    await server.start()
    print(json.dumps({"service": "farm-service", "event": "started", "port": 50051}), flush=True)
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        await pool.close()


if __name__ == "__main__":
    asyncio.run(serve())
