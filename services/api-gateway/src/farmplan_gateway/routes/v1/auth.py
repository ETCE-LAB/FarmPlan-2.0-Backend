"""Authentication transport; refresh credentials are never returned in JSON."""

from fastapi import Depends, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool


def register(app, deps):
    def add_auth(path, rpc_name, request_model=None, status_code=200):
        if request_model:
            async def endpoint(request, response: Response):
                fields = request.model_dump()
                result = await run_in_threadpool(getattr(deps.identity_client, rpc_name),
                    getattr(deps.identity_pb2, rpc_name + "Request")(**fields), timeout=10)
                return deps.auth_payload(result, response)
            endpoint.__annotations__["request"] = request_model
        else:
            async def endpoint(response: Response):
                result = await run_in_threadpool(deps.identity_client.CreateGuestSession,
                    deps.identity_pb2.GuestSessionRequest(), timeout=10)
                return deps.auth_payload(result, response)
        endpoint.__name__ = rpc_name
        app.add_api_route("/api/v1/auth/" + path, endpoint, methods=["POST"],
            status_code=status_code, response_model=deps.AuthResponse,
            dependencies=[Depends(deps.cookie_origin)], tags=["authentication"])

    add_auth("register", "Register", deps.RegisterRequest, 201)
    add_auth("login", "Login", deps.LoginRequest)
    add_auth("guest", "CreateGuestSession")

    async def refresh(request: Request, response: Response):
        token = request.cookies.get("refresh_token")
        if not token:
            raise HTTPException(401, "Refresh cookie required.")
        result = await run_in_threadpool(deps.identity_client.Refresh,
            deps.identity_pb2.RefreshRequest(refresh_token=token), timeout=10)
        return deps.auth_payload(result, response)

    async def logout(request: Request):
        token = request.cookies.get("refresh_token")
        if token:
            await run_in_threadpool(deps.identity_client.Logout,
                deps.identity_pb2.LogoutRequest(refresh_token=token), timeout=10)
        response = Response(status_code=204)
        deps.clear_refresh_cookie(response)
        return response

    app.add_api_route("/api/v1/auth/refresh", refresh, methods=["POST"],
        response_model=deps.AuthResponse, dependencies=[Depends(deps.cookie_origin)], tags=["authentication"])
    app.add_api_route("/api/v1/auth/logout", logout, methods=["POST"], status_code=204,
        dependencies=[Depends(deps.cookie_origin)], tags=["authentication"])
