"""Overview aggregates independent Fields without loading Farm resources."""
import asyncio
from copy import deepcopy
import uuid

import grpc
import pytest
from farm.v1 import farm_pb2, farm_pb2_grpc
from farmplan_farm.main import FarmService, JsonStore

OWNER = "9a62eedd-7c33-4c4b-b9dc-99b4c7b7e8d4"
OTHER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


class Abort(Exception):
    pass


class Context:
    async def abort(self, code, message):
        raise Abort(code)


def request(owner=OWNER):
    return farm_pb2.GetOverviewRequest(owner_id=owner)


def populated_store():
    store = JsonStore()
    row = next(iter(store.rows.values()))
    row["data"]["fields"] = [{"id": "embedded"}] * 5
    other = deepcopy(row)
    other.update(id=uuid.uuid4(), owner_id=uuid.UUID(OTHER))
    store.rows[other["id"]] = other
    for _ in range(3):
        key = uuid.uuid4()
        store.fields[key] = {"farmId": str(other["id"])}
    own = deepcopy(row)
    own["id"] = uuid.uuid4()
    store.rows[own["id"]] = own
    return store


def test_json_counts_and_owner_isolation():
    async def scenario():
        service = FarmService(populated_store())
        for owner, expected in [(OWNER, (2, 1)), (OTHER, (1, 3)), (str(uuid.uuid4()), (0, 0))]:
            result = await service.GetOverview(request(owner), Context())
            assert (result.farm_count, result.field_count) == expected
        service.pool.rows.clear()
        service.pool.fields.clear()
        assert await service.GetOverview(request(), Context()) == farm_pb2.GetOverviewResponse()
    asyncio.run(scenario())


@pytest.mark.parametrize("owner", ["", "invalid", "guest-session"])
def test_invalid_uuid_before_storage(owner):
    with pytest.raises(Abort) as error:
        asyncio.run(FarmService(object()).GetOverview(request(owner), Context()))
    assert error.value.args == (grpc.StatusCode.INVALID_ARGUMENT,)


@pytest.mark.parametrize("counts", [(0, 0), (4, 12)])
def test_sql_single_parameterized_owner_scoped_aggregate(counts):
    class Pool:
        calls = []

        async def fetchrow(self, sql, *args):
            self.calls.append((sql, args))
            return dict(farm_count=counts[0], field_count=counts[1])

    pool = Pool()
    result = asyncio.run(FarmService(pool).GetOverview(request(), Context()))
    assert (result.farm_count, result.field_count) == counts
    assert len(pool.calls) == 1
    sql, args = pool.calls[0]
    normalized = " ".join(sql.lower().split())
    assert args == (uuid.UUID(OWNER),)
    assert normalized.count("count(*)") == 2
    assert "from farms where owner_id=$1" in normalized
    assert "join farms as farm on farm.id=field.farm_id" in normalized
    assert "where farm.owner_id=$1" in normalized
    assert "data" not in normalized and "select *" not in normalized


def test_overview_generated_grpc_loopback():
    async def scenario():
        server = grpc.aio.server()
        farm_pb2_grpc.add_FarmServiceServicer_to_server(FarmService(populated_store()), server)
        port = server.add_insecure_port("127.0.0.1:0")
        await server.start()
        try:
            async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
                client = farm_pb2_grpc.FarmServiceStub(channel)
                result = await client.GetOverview(request(), timeout=5)
                assert (result.farm_count, result.field_count) == (2, 1)
                result = await client.GetOverview(request(OTHER), timeout=5)
                assert (result.farm_count, result.field_count) == (1, 3)
                with pytest.raises(grpc.aio.AioRpcError) as error:
                    await client.GetOverview(request("invalid"), timeout=5)
                assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        finally:
            await server.stop(0)
    asyncio.run(scenario())
