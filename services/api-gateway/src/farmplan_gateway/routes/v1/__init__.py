"""Route registration for the public v1 API."""

from farmplan_gateway.routes.v1.auth import register as register_auth_routes
from farmplan_gateway.routes.v1.farms import register as register_farm_routes
from farmplan_gateway.routes.v1.fields import register as register_field_routes
from farmplan_gateway.routes.v1.modules import register as register_module_routes
from farmplan_gateway.routes.v1.users import register as register_user_routes
from farmplan_gateway.routes.v1.overview import register as register_overview_routes


def register_v1_routes(app, deps) -> None:
    register_auth_routes(app, deps)
    register_user_routes(app, deps)
    register_module_routes(app, deps)
    register_farm_routes(app, deps)
    register_field_routes(app, deps)
    register_overview_routes(app, deps)
