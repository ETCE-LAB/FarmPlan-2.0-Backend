"""Version 1 module discovery and access routes."""

from typing import Any

from fastapi import Depends


def register(app, deps) -> None:
    async def list_modules(user: Any = Depends(deps.current_user)) -> dict[str, list[dict[str, object]]]:
        return {
            "modules": [
                {
                    "id": module_id,
                    "enabled": module_id in deps.ENABLED_MODULES,
                    "available_to_guest": module_id in deps.GUEST_ENABLED_MODULES,
                    "accessible": module_id in deps.ENABLED_MODULES
                    and (user.account_type != "guest" or module_id in deps.GUEST_ENABLED_MODULES),
                }
                for module_id in sorted(deps.KNOWN_MODULES)
            ]
        }

    app.add_api_route("/api/v1/modules", list_modules, methods=["GET"], tags=["modules"])

    async def check_module_access(
        module_id: str, user: Any = Depends(deps.current_user)
    ) -> dict[str, str | bool]:
        deps.require_module(module_id, user.account_type)
        return {"module_id": module_id, "accessible": True, "account_type": user.account_type}

    app.add_api_route(
        "/api/v1/modules/{module_id}/access",
        check_module_access,
        methods=["GET"],
        tags=["modules"],
    )
