"""Global authenticated overview, initially aggregating Farm-owned statistics."""
from typing import Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from .fields import call_farm


class OverviewResponse(BaseModel):
    farmCount: int = Field(ge=0)
    fieldCount: int = Field(ge=0)


def register(app, deps):
    async def get_overview(user: Any = Depends(deps.current_user)):

        if user.account_type == "guest":
            raise HTTPException(403)
        result = await call_farm(deps, "GetOverview", deps.farm_pb2.GetOverviewRequest(owner_id=user.user_id))
        return dict(farmCount=result.farm_count, fieldCount=result.field_count)

    app.add_api_route("/api/v1/overview", get_overview, methods=["GET"],
                      response_model=OverviewResponse, tags=["overview"])
