"""User transport; Identity owns profile and account authorization."""

from fastapi import Depends, Response
from starlette.concurrency import run_in_threadpool


def register(app, deps):
    async def get_me(user=Depends(deps.current_user)):
        return deps.profile_payload(user)

    async def update_me(request, token=Depends(deps.access_token)):
        result = await run_in_threadpool(deps.identity_client.UpdateProfile,
            deps.identity_pb2.UpdateProfileRequest(access_token=token, display_name=request.displayName),
            timeout=10)
        return deps.profile_payload(result)

    async def password(request, token=Depends(deps.access_token)):
        await run_in_threadpool(deps.identity_client.ChangePassword,
            deps.identity_pb2.ChangePasswordRequest(access_token=token,
                current_password=request.currentPassword, new_password=request.newPassword), timeout=10)
        return Response(status_code=204)

    async def delete_me(token=Depends(deps.access_token)):
        await run_in_threadpool(deps.identity_client.DeleteSelf,
            deps.identity_pb2.DeleteSelfRequest(access_token=token), timeout=10)
        return Response(status_code=204)

    update_me.__annotations__["request"] = deps.ProfileUpdateRequest
    password.__annotations__["request"] = deps.PasswordRequest
    app.add_api_route("/api/v1/users/me", get_me, methods=["GET"], response_model=deps.UserResponse, tags=["users"])
    app.add_api_route("/api/v1/users/me", update_me, methods=["PATCH"], response_model=deps.UserResponse, tags=["users"])
    app.add_api_route("/api/v1/users/me/password", password, methods=["POST"], status_code=204, tags=["users"])
    app.add_api_route("/api/v1/users/me", delete_me, methods=["DELETE"], status_code=204, tags=["users"])
