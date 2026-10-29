"""Version 1 user routes."""

from typing import Any

from fastapi import Depends


def register(app, deps) -> None:
    async def get_me(user: Any = Depends(deps.current_user)) -> dict[str, str]:
        return {
            "user_id": user.user_id,
            "email": user.email,
            "display_name": user.display_name,
            "account_type": user.account_type,
        }

    app.add_api_route("/api/v1/users/me", get_me, methods=["GET"], tags=["users"])
