"""Generated Field RPC acceptance over a real loopback gRPC channel."""
import asyncio
from copy import deepcopy
import json


import grpc
import pytest
from farm.v1 import farm_pb2, farm_pb2_grpc
from farmplan_farm.main import FarmService, JsonStore
from farmplan_farm.geometry import Invalid, field_data, metrics, polygon

OWNER = "9a62eedd-7c33-4c4b-b9dc-99b4c7b7e8d4"
FARM = "c56c779b-2ee1-4a15-af56-7a3c1c4fb3c8"
OTHER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
GEOMETRY = {"type":"Polygon","coordinates":[[[10,50],[10.01,50],[10.01,50.01],[10,50.01],[10,50]]]}


def test_field_generated_rpc_lifecycle_rollback_and_permissions():
    async def scenario():
        store = JsonStore()
        server = grpc.aio.server()
        farm_pb2_grpc.add_FarmServiceServicer_to_server(FarmService(store),server)
        port = server.add_insecure_port("127.0.0.1:0")
        await server.start()
        try:
            async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
                client = farm_pb2_grpc.FarmServiceStub(channel)
                async def call(operation, owner=OWNER, field_id="", data=None, **kwargs):
                    return json.loads((await client.Fields(farm_pb2.FieldRequest(owner_id=owner,farm_id=FARM,field_id=field_id,operation=operation,data_json=json.dumps(data),**kwargs),timeout=5)).data_json)
                initial = await call("list")
                item = await call("create",data=dict(name="RPC",geometry=GEOMETRY))
                assert item["farmId"] == FARM
                field_id = item["id"]
                assert await call("get",field_id=field_id) == item
                for operation in ("get","patch","delete"):
                    with pytest.raises(grpc.aio.AioRpcError) as error:
                        await call(operation,owner=OTHER,field_id=field_id,data={"name":"denied"})
                    assert error.value.code() == grpc.StatusCode.NOT_FOUND
                snapshot = deepcopy(store.fields)
                for operation, data in [
                    ("patch",{"name":"must not change","soilPh":True}),
                    ("patch",{"name":"must not change","geometry":{"type":"Polygon","coordinates":[[[10,50],[10.01,50.01],[10,50.01],[10.01,50],[10,50]]]}}),
                    ("bulk",{"items":[dict(name="first",geometry=GEOMETRY),dict(name="invalid",geometry=None)]}),
                ]:
                    with pytest.raises(grpc.aio.AioRpcError) as error:
                        await call(operation,field_id=field_id if operation=="patch" else "",data=data)
                    assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
                    assert json.loads(error.value.details())["details"]
                    assert store.fields == snapshot
                updated = await call("patch",field_id=field_id,data={"name":"Updated"})
                assert updated["name"] == "Updated" and updated["createdAt"] == item["createdAt"]
                imported = await call("bulk",data={"type":"FeatureCollection","features":[{"type":"Feature","geometry":GEOMETRY,"properties":{"name":"Imported"}}]})
                assert len(imported["items"]) == 1
                assert (await call("list",page=2,page_size=1))["total"] == initial["total"]+2
                await call("delete",field_id=field_id)
                with pytest.raises(grpc.aio.AioRpcError) as error:
                    await call("get",field_id=field_id)
                assert error.value.code() == grpc.StatusCode.NOT_FOUND
                await client.DeleteFarm(farm_pb2.FarmIdRequest(owner_id=OWNER,farm_id=FARM),timeout=5)
                assert not store.fields
        finally:
            await server.stop(0)
    asyncio.run(scenario())


@pytest.mark.parametrize("coordinate", [True, float("nan"), float("inf"), -181, 181, "10", None])
def test_service_rejects_nonfinite_bool_and_out_of_range(coordinate):
    geometry = deepcopy(GEOMETRY)
    geometry["coordinates"][0][0][0] = coordinate
    geometry["coordinates"][0][-1][0] = coordinate
    with pytest.raises(Invalid):
        field_data(dict(name="invalid",geometry=geometry))


def test_geodesic_orientation_and_hole_metrics():
    original = polygon(GEOMETRY)
    reversed_geometry = deepcopy(GEOMETRY)
    reversed_geometry["coordinates"][0].reverse()
    assert metrics(original) == pytest.approx(metrics(polygon(reversed_geometry)))
    holed = deepcopy(GEOMETRY)
    hole = [[10.002,50.002],[10.003,50.002],[10.003,50.003],[10.002,50.003],[10.002,50.002]]
    holed["coordinates"].append(hole)
    area, perimeter = metrics(polygon(holed))
    assert area < metrics(original)[0] and perimeter > metrics(original)[1]


def test_service_limits_and_holes_outside():
    for geometry in [
        {"type":"Polygon","coordinates":[GEOMETRY["coordinates"][0]*1001]},
        {"type":"Polygon","coordinates":GEOMETRY["coordinates"]*101},
        {"type":"Polygon","coordinates":GEOMETRY["coordinates"]+[[[11,51],[11.1,51],[11.1,51.1],[11,51]]]},
    ]:
        with pytest.raises(Invalid):
            polygon(geometry)


def test_sql_adapter_transaction_control_and_bulk_rollback():
    # A SQL double verifies orchestration, not PostgreSQL FK/locking semantics.
    from contextlib import asynccontextmanager
    import uuid

    class Failure(Exception):
        pass

    class Context:
        async def abort(self,code,message):
            raise Failure(code,message)

    class Connection:
        def __init__(self):
            self.fields = {}
            self.fail_insert = False
            self.in_transaction = False
            self.rollbacks = 0

        @asynccontextmanager
        async def transaction(self):
            before = deepcopy(self.fields)
            self.in_transaction = True
            try:
                yield
            except Exception:
                self.fields = before
                self.rollbacks += 1
                raise
            finally:
                self.in_transaction = False

        async def fetchrow(self,query,*args):
            assert self.in_transaction
            if "FROM farms" in query:
                assert "FOR UPDATE" in query
                return {"data":{}} if args[1] == uuid.UUID(OWNER) else None
            item = self.fields.get(args[0])
            return {"data":json.dumps(item)} if item else None

        async def fetch(self,query,*args):
            return [{"data":json.dumps(f)} for f in self.fields.values()]

        async def execute(self,query,*args):
            assert self.in_transaction
            if query.startswith("INSERT"):
                if self.fail_insert and self.fields:
                    raise RuntimeError("synthetic database failure")
                self.fields[args[0]] = json.loads(args[2])
            elif query.startswith("UPDATE"):
                self.fields[args[0]] = json.loads(args[1])
            else:
                del self.fields[args[0]]

    class Pool:
        def __init__(self):
            self.connection = Connection()
        @asynccontextmanager
        async def acquire(self):
            yield self.connection

    async def scenario():
        pool = Pool()
        service = FarmService(pool)
        async def call(operation,data=None,field_id=""):
            result = await service.Fields(farm_pb2.FieldRequest(owner_id=OWNER,farm_id=FARM,field_id=field_id,operation=operation,data_json=json.dumps(data)),Context())
            return json.loads(result.data_json)
        batch = {"items":[dict(name="one",geometry=GEOMETRY),dict(name="two",geometry=GEOMETRY)]}
        pool.connection.fail_insert = True
        with pytest.raises(RuntimeError):
            await call("bulk",batch)
        assert not pool.connection.fields and pool.connection.rollbacks == 1
        pool.connection.fail_insert = False
        result = await call("bulk",batch)
        assert len(result["items"]) == 2
        before = deepcopy(pool.connection.fields)
        with pytest.raises(Failure):
            await call("bulk",{"items":[batch["items"][0],{"name":"invalid","geometry":None}]})
        assert pool.connection.fields == before
        item = result["items"][0]
        updated = await call("patch",{"soilPh":7},item["id"])
        assert updated["soilPh"] == 7
        assert (await call("get",field_id=item["id"])) == updated
        assert (await call("list"))["total"] == 2
        await call("delete",field_id=item["id"])
        assert (await call("list"))["total"] == 1
    asyncio.run(scenario())
