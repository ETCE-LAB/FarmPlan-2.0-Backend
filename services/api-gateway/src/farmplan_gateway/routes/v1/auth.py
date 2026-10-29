"""Version 1 authentication routes."""

from typing import Any

from starlette.concurrency import run_in_threadpool


def register(app, deps) -> None:
    async def register_account(request: Any) -> dict[str, str]:
        try:
            response = await run_in_threadpool(
                deps.identity_client.Register,
                deps.identity_pb2.RegisterRequest(
                    email=request.email,
                    password=request.password,
                    display_name=request.display_name,
                ),
                timeout=10,
            )
            return deps.auth_payload(response)
        except deps.grpc.RpcError as error:
            deps.raise_http_error(error)
            raise RuntimeError("unreachable") from error

    register_account.__annotations__["request"] = deps.RegisterRequest
    app.add_api_route(
        "/api/v1/auth/register",
        register_account,
        methods=["POST"],
        status_code=201,
        tags=["authentication"],
    )

    async def login(request: Any) -> dict[str, str]:
        try:
            response = await run_in_threadpool(
                deps.identity_client.Login,
                deps.identity_pb2.LoginRequest(email=request.email, password=request.password),
                timeout=10,
            )
            return deps.auth_payload(response)
        except deps.grpc.RpcError as error:
            deps.raise_http_error(error)
            raise RuntimeError("unreachable") from error

    login.__annotations__["request"] = deps.LoginRequest
    app.add_api_route(
        "/api/v1/auth/login", login, methods=["POST"], tags=["authentication"]
    )

    async def create_guest_session() -> dict[str, str]:
        try:
            response = await run_in_threadpool(
                deps.identity_client.CreateGuestSession,
                deps.identity_pb2.GuestSessionRequest(),
                timeout=10,
            )
            return deps.auth_payload(response)
        except deps.grpc.RpcError as error:
            deps.raise_http_error(error)
            raise RuntimeError("unreachable") from error

    app.add_api_route(
        "/api/v1/auth/guest",
        create_guest_session,
        methods=["POST"],
        tags=["authentication"],
    )
