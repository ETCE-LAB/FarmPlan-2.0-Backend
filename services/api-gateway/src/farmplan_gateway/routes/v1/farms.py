"""Version 1 farm routes; identity always comes from the verified bearer token."""

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends
from starlette.concurrency import run_in_threadpool


def register(app, deps) -> None:
    async def list_farms(user: Any = Depends(deps.current_user)) -> dict[str, object]:
        deps.require_module("farms", user.account_type)
        try:
            response = await run_in_threadpool(
                deps.farm_client.ListFarms,
                deps.farm_pb2.ListFarmsRequest(owner_id=user.user_id),
                timeout=10,
            )
            return {"status": "ok", "farms": [deps.farm_from_proto(farm) for farm in response.farms]}
        except deps.grpc.RpcError as error:
            deps.raise_farm_http_error(error)
            raise RuntimeError("unreachable") from error

    app.add_api_route("/api/v1/farms", list_farms, methods=["GET"], tags=["farms"])

    async def create_farm(
        request: Any, user: Any = Depends(deps.current_user)
    ) -> dict[str, object]:
        deps.require_module("farms", user.account_type)
        data = request.model_dump(mode="json", exclude={"createdAt"})
        data["createdAt"] = datetime.now(UTC).isoformat()
        try:
            response = await run_in_threadpool(
                deps.farm_client.CreateFarm,
                deps.farm_pb2.FarmRequest(owner_id=user.user_id, data_json=json.dumps(data)),
                timeout=10,
            )
            return {"status": "ok", "farm": deps.farm_from_proto(response.farm)}
        except deps.grpc.RpcError as error:
            deps.raise_farm_http_error(error)
            raise RuntimeError("unreachable") from error

    create_farm.__annotations__["request"] = deps.FarmCreateRequest
    app.add_api_route(
        "/api/v1/farms", create_farm, methods=["POST"], status_code=201, tags=["farms"]
    )

    async def update_farm(
        farm_id: str, request: Any, user: Any = Depends(deps.current_user)
    ) -> dict[str, object]:
        deps.require_module("farms", user.account_type)
        data = request.model_dump(mode="json", exclude_unset=True, exclude={"createdAt"})
        try:
            response = await run_in_threadpool(
                deps.farm_client.UpdateFarm,
                deps.farm_pb2.UpdateFarmRequest(
                    owner_id=user.user_id, farm_id=farm_id, data_json=json.dumps(data)
                ),
                timeout=10,
            )
            return {"status": "ok", "farm": deps.farm_from_proto(response.farm)}
        except deps.grpc.RpcError as error:
            deps.raise_farm_http_error(error)
            raise RuntimeError("unreachable") from error

    update_farm.__annotations__["request"] = deps.FarmUpdateRequest
    app.add_api_route(
        "/api/v1/farms/{farm_id}", update_farm, methods=["PUT"], tags=["farms"]
    )

    async def delete_farm(farm_id: str, user: Any = Depends(deps.current_user)) -> dict[str, object]:
        deps.require_module("farms", user.account_type)
        try:
            response = await run_in_threadpool(
                deps.farm_client.DeleteFarm,
                deps.farm_pb2.FarmIdRequest(owner_id=user.user_id, farm_id=farm_id),
                timeout=10,
            )
            return {"status": "ok", "deleted": response.deleted}
        except deps.grpc.RpcError as error:
            deps.raise_farm_http_error(error)
            raise RuntimeError("unreachable") from error

    app.add_api_route(
        "/api/v1/farms/{farm_id}", delete_farm, methods=["DELETE"], tags=["farms"]
    )
