import asyncio
import json

import grpc
import pytest
from farm.v1 import farm_pb2, farm_pb2_grpc
from farmplan_farm.main import FarmService, JsonStore, storage_backend

OWNER = "9a62eedd-7c33-4c4b-b9dc-99b4c7b7e8d4"
OTHER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def test_json_application_over_generated_grpc(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FARM_STORAGE_BACKEND", "json")
    assert storage_backend() == "json"

    async def scenario():
        server = grpc.aio.server()
        farm_pb2_grpc.add_FarmServiceServicer_to_server(FarmService(JsonStore()), server)
        port = server.add_insecure_port("127.0.0.1:0")
        await server.start()
        try:
            async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
                client = farm_pb2_grpc.FarmServiceStub(channel)
                listed = await client.ListFarms(farm_pb2.ListFarmsRequest(owner_id=OWNER), timeout=5)
                assert listed.total == 1
                created = await client.CreateFarm(farm_pb2.FarmRequest(owner_id=OWNER, data_json=json.dumps({"name": "Synthetic RPC farm", "fields": [{"id": "legacy", "area": 12}], "template": {"items": []}})), timeout=5)
                resource = json.loads(created.farm.data_json)
                assert resource["summary"]["fieldAreaM2"] == 0
                farm_id = created.farm.id
                updated = await client.UpdateFarm(farm_pb2.UpdateFarmRequest(owner_id=OWNER, farm_id=farm_id, data_json='{"notes":"updated"}'), timeout=5)
                assert json.loads(updated.farm.data_json)["summary"]["fieldCount"] == 0
                for method, request in [
                    (client.GetFarm, farm_pb2.FarmIdRequest(owner_id=OTHER, farm_id=farm_id)),
                    (client.UpdateFarm, farm_pb2.UpdateFarmRequest(owner_id=OTHER, farm_id=farm_id, data_json='{"notes":"denied"}')),
                    (client.DeleteFarm, farm_pb2.FarmIdRequest(owner_id=OTHER, farm_id=farm_id)),
                ]:
                    with pytest.raises(grpc.aio.AioRpcError) as error:
                        await method(request, timeout=5)
                    assert error.value.code() == grpc.StatusCode.NOT_FOUND
                await client.DeleteFarm(farm_pb2.FarmIdRequest(owner_id=OWNER, farm_id=farm_id), timeout=5)
                with pytest.raises(grpc.aio.AioRpcError) as error:
                    await client.GetFarm(farm_pb2.FarmIdRequest(owner_id=OWNER, farm_id=farm_id), timeout=5)
                assert error.value.code() == grpc.StatusCode.NOT_FOUND
                with pytest.raises(grpc.aio.AioRpcError) as error:
                    await client.CreateFarm(farm_pb2.FarmRequest(owner_id="guest-session", data_json='{"name":"denied"}'), timeout=5)
                assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        finally:
            await server.stop(0)
    asyncio.run(scenario())
