"""Field HTTP acceptance with the real application and synthetic JSON state."""
import asyncio
import threading
import grpc
import pytest
from test_farms import setup, HEADERS, ID, OWNER

BASE = f"/api/v1/farms/{ID}/fields"


def square(x=10, y=50, size=.01):
    return {"type": "Polygon", "coordinates": [[[x,y],[x+size,y],[x+size,y+size],[x,y+size],[x,y]]]}


def payload():
    return dict(name="Test field", geometry=square())


def create(client, data=None):
    response = client.post(BASE, headers=HEADERS, json=data or payload())
    assert response.status_code == 201, response.text
    return response.json()


def test_field_lifecycle_pagination_summary_and_cascade(setup):
    client, service, identity = setup
    data = create(client)
    path = f'/api/v1/fields/{data["id"]}'
    assert data["farmId"] == ID
    assert 790000 < data["areaM2"] < 810000
    assert data["netAreaM2"] == data["areaM2"]
    assert 3600 < data["perimeterM"] < 3700
    assert data["createdAt"] == data["updatedAt"]
    assert client.get(path, headers=HEADERS).json() == data
    page = client.get(BASE + "?page=2&pageSize=1", headers=HEADERS).json()
    assert page["total"] == 2 and page["page"] == 2 and page["pageSize"] == 1
    assert client.get(BASE + "?page=9", headers=HEADERS).json()["items"] == []
    changed = client.patch(path, headers=HEADERS, json={"soilPh": 6.5, "irrigation": "drip", "autoSpacing": True}).json()
    assert changed["soilPh"] == 6.5 and changed["autoSpacing"] is True
    assert changed["createdAt"] == data["createdAt"] and changed["updatedAt"] >= data["updatedAt"]
    summary = client.get(f"/api/v1/farms/{ID}", headers=HEADERS).json()["summary"]
    assert summary["fieldCount"] == 2 and summary["fieldAreaM2"] > data["areaM2"]
    assert client.delete(path, headers=HEADERS).status_code == 204
    assert client.get(path, headers=HEADERS).status_code == 404
    remaining = client.get(BASE, headers=HEADERS).json()["items"][0]["id"]
    assert client.delete(f"/api/v1/farms/{ID}", headers=HEADERS).status_code == 204
    assert client.get(f"/api/v1/fields/{remaining}", headers=HEADERS).status_code == 404
    assert not service.pool.fields


def test_boundary_containment_and_atomic_boundary_patch(setup):
    client, _, _ = setup
    boundary = square(9.99,49.99,.1)
    response = client.patch(f"/api/v1/farms/{ID}", headers=HEADERS, json={"boundary":boundary})
    assert response.status_code == 200
    assert response.json()["boundaryAreaM2"] > 0 and response.json()["boundaryPerimeterM"] > 0
    create(client)
    bad = client.post(BASE, headers=HEADERS, json=dict(name="outside",geometry=square(11)))
    assert bad.status_code == 422
    assert bad.json()["error"]["details"][0]["code"] == "outside_farm_boundary"
    before = client.get(f"/api/v1/farms/{ID}", headers=HEADERS).json()
    bad = client.patch(f"/api/v1/farms/{ID}", headers=HEADERS, json={"name":"must not change", "boundary":square(11)})
    assert bad.status_code == 422
    assert client.get(f"/api/v1/farms/{ID}", headers=HEADERS).json() == before


def test_farm_holes_and_boundary_touching(setup):
    client, _, _ = setup
    boundary = square(9.99,49.99,.1)
    boundary["coordinates"].append(square(10.02,50.02,.01)["coordinates"][0])
    assert client.patch(f"/api/v1/farms/{ID}",headers=HEADERS,json={"boundary":boundary}).status_code == 200
    response = client.post(BASE,headers=HEADERS,json=dict(name="in farm hole",geometry=square(10.022,50.022,.001)))
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["code"] == "outside_farm_boundary"
    # Field exterior may coincide with the farm exterior.
    create(client,dict(name="touching",geometry=square(9.99,49.99,.01)))
    assert client.patch(f"/api/v1/farms/{ID}",headers=HEADERS,json={"boundary":None}).json()["boundaryAreaM2"] is None


def test_exclusion_holes_and_metrics(setup):
    client, _, _ = setup
    geometry = square()
    geometry["coordinates"].append(square(10.001,50.001,.001)["coordinates"][0])
    exclusion = {"type":"MultiPolygon", "coordinates":[square(10.004,50.004,.001)["coordinates"]]}
    data = create(client, dict(name="holes",geometry=geometry,excludedZones=exclusion))
    assert 0 < data["netAreaM2"] < data["areaM2"]
    cleared = client.patch(f'/api/v1/fields/{data["id"]}',headers=HEADERS,json={"excludedZones":None,"soilPh":None}).json()
    assert cleared["netAreaM2"] == cleared["areaM2"] and cleared["soilPh"] is None
    for coordinates in [
        [square(10.001,50.001,.001)["coordinates"]], # existing hole
        [square(10,50,.001)["coordinates"]], # touches exterior
        [square(11,50,.001)["coordinates"]],
        [square(10.004,50.004,.002)["coordinates"],square(10.005,50.005,.002)["coordinates"]],
    ]:
        bad = client.post(BASE, headers=HEADERS, json=dict(name="bad",geometry=geometry,excludedZones=dict(type="MultiPolygon",coordinates=coordinates)))
        assert bad.status_code == 422


@pytest.mark.parametrize("patch", [{}, {"id":OWNER}, {"farmId":ID}, {"name":None}, {"geometry":None}, {"soilPh":True}, {"soilPh":15}, {"autoSpacing":1}, {"irrigation":"invalid"}, {"name":" "}])
def test_patch_rejection_preserves_all_state(setup, patch):
    client, _, _ = setup
    data = create(client)
    path = f'/api/v1/fields/{data["id"]}'
    response = client.patch(path, headers=HEADERS, json=patch)
    assert response.status_code == 422
    assert client.get(path, headers=HEADERS).json() == data


@pytest.mark.parametrize("coordinates", [
    [[[10,50],[10.01,50.01],[10,50.01],[10.01,50],[10,50]]],
    [[[10,50],[10.01,50],[10.01,50.01],[10,50.01]]],
    [[[True,50],[10.01,50],[10.01,50.01],[True,50]]],
    [[[181,50],[181.01,50],[181.01,50.01],[181,50]]],
    [[[10,50,0],[10.01,50],[10.01,50.01],[10,50,0]]],
    [[[10,50],[10,50],[10,50],[10,50]]],
    [[[179,50],[-179,50],[-179,51],[179,50]]],
])
def test_geometry_negatives(setup, coordinates):
    client, _, _ = setup
    before = client.get(BASE, headers=HEADERS).json()
    response = client.post(BASE, headers=HEADERS, json=dict(name="bad",geometry=dict(type="Polygon",coordinates=coordinates)))
    assert response.status_code == 422
    assert client.get(BASE, headers=HEADERS).json() == before


def test_self_intersection_code_and_patch_rollback(setup):
    client, _, _ = setup
    data = create(client)
    path = f'/api/v1/fields/{data["id"]}'
    bowtie = dict(type="Polygon",coordinates=[[[10,50],[10.01,50.01],[10,50.01],[10.01,50],[10,50]]])
    response = client.patch(path, headers=HEADERS, json=dict(name="changed",geometry=bowtie))
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["code"] == "self_intersecting"
    assert client.get(path, headers=HEADERS).json() == data


def test_bulk_shapes_and_rollback(setup):
    client, _, _ = setup
    before = client.get(BASE, headers=HEADERS).json()
    bad = payload()
    bad["geometry"]["coordinates"][0][-1] = [11,51]
    response = client.post(BASE+":bulk", headers=HEADERS, json={"items":[payload(),bad]})
    assert response.status_code == 422
    assert client.get(BASE, headers=HEADERS).json() == before
    for document in [{"items":[payload(),payload()]}, {"type":"FeatureCollection","features":[{"type":"Feature","geometry":square(),"properties":{"name":"Imported"}}]}]:
        response = client.post(BASE+":bulk", headers=HEADERS,json=document)
        assert response.status_code == 201, response.text
        assert response.json()["items"]
    for document in [{"items":[]},{"items":[payload()]*101},[],{"type":"FeatureCollection","features":[]},{"items":[dict(payload(),id=OWNER)]}]:
        assert client.post(BASE+":bulk",headers=HEADERS,json=document).status_code == 422


def test_auth_ownership_and_guests(setup,monkeypatch):
    client, _, identity = setup
    data = create(client)
    path = f'/api/v1/fields/{data["id"]}'
    assert client.get(BASE).status_code == 401
    identity.owner = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    for method, url, body in [("get",BASE,None),("post",BASE,payload()),("post",BASE+":bulk",{"items":[payload()]}),("get",path,None),("patch",path,{"name":"foreign"}),("delete",path,None)]:
        kwargs = {"headers":HEADERS}
        if body is not None:
            kwargs["json"] = body
        assert getattr(client,method)(url,**kwargs).status_code == 404
    identity.account = "guest"
    monkeypatch.setattr(__import__("farmplan_gateway.main",fromlist=["GUEST_ENABLED_MODULES"]),"GUEST_ENABLED_MODULES",{"farms"})
    assert client.get(BASE,headers=HEADERS).status_code == 403
    assert client.post(BASE,headers=HEADERS,json=payload()).status_code == 403
    assert client.post(BASE+":bulk",headers=HEADERS,json={"items":[payload()]}).status_code == 403
    assert client.get(path,headers=HEADERS).status_code == 403
    assert client.patch(path,headers=HEADERS,json={"name":"denied"}).status_code == 403
    assert client.delete(path,headers=HEADERS).status_code == 403


def test_openapi_response_and_request_schemas(setup):
    client, _, _ = setup
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/api/v1/fields/{field_id}"]["patch"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/FieldResponse")
    assert schema["components"]["schemas"]["FieldResponse"]["properties"]["geometry"]["$ref"].endswith("/Polygon")
    assert client.get(BASE+"?page=0",headers=HEADERS).status_code == 422
    assert client.get(BASE+"?pageSize=101",headers=HEADERS).status_code == 422


def test_gateway_to_real_loopback_farm_grpc(setup, monkeypatch):
    from farm.v1 import farm_pb2_grpc
    from farmplan_gateway import main as gateway
    from farmplan_farm.main import FarmService, JsonStore
    client, _, _ = setup
    ready = threading.Event()
    state = {}

    async def serve():
        server = grpc.aio.server()
        farm_pb2_grpc.add_FarmServiceServicer_to_server(FarmService(JsonStore()),server)
        state["port"] = server.add_insecure_port("127.0.0.1:0")
        state["loop"] = asyncio.get_running_loop()
        state["stop"] = asyncio.Event()
        await server.start()
        ready.set()
        try:
            await state["stop"].wait()
        finally:
            await server.stop(0)

    thread = threading.Thread(target=lambda: asyncio.run(serve()), daemon=True)
    thread.start()
    assert ready.wait(5)
    channel = grpc.insecure_channel(f'127.0.0.1:{state["port"]}')
    monkeypatch.setattr(gateway,"farm_client",farm_pb2_grpc.FarmServiceStub(channel))
    try:
        data = create(client)
        path = f'/api/v1/fields/{data["id"]}'
        assert client.get(path,headers=HEADERS).json() == data
        bowtie = dict(type="Polygon",coordinates=[[[10,50],[10.01,50.01],[10,50.01],[10.01,50],[10,50]]])
        response = client.patch(path,headers=HEADERS,json=dict(name="rejected",geometry=bowtie))
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["code"] == "self_intersecting"
        assert client.get(path,headers=HEADERS).json() == data
    finally:
        channel.close()
        state["loop"].call_soon_threadsafe(state["stop"].set)
        thread.join(timeout=5)
        assert not thread.is_alive()


@pytest.mark.parametrize("code,status", [(grpc.StatusCode.UNAVAILABLE,503),(grpc.StatusCode.DEADLINE_EXCEEDED,504),(grpc.StatusCode.NOT_FOUND,404)])
def test_field_upstream_error_envelope(setup,monkeypatch,code,status):
    from farmplan_gateway import main as gateway
    from test_farms import Error
    client, _, _ = setup
    class Failed:
        def Fields(self,request,timeout=None):
            raise Error(code)
    monkeypatch.setattr(gateway,"farm_client",Failed())
    response = client.get(BASE,headers=HEADERS)
    assert response.status_code == status
    assert set(response.json()) == {"error"}
