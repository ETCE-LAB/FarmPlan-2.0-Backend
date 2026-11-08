"""Bounded RFC 7946 geometry; topology in lon/lat, metrics on WGS84."""
import math
from pyproj import Geod
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from shapely.validation import explain_validity

GEOD = Geod(ellps="WGS84")


class Invalid(ValueError):
    def __init__(self, path, code="invalid_value", message="Invalid value."):
        self.details = [dict(path=path, code=code, message=message)]
        super().__init__(message)


def polygon(value, path="geometry", multi=False):
    kind = "MultiPolygon" if multi else "Polygon"
    if not isinstance(value, dict) or set(value) != {"type", "coordinates"} or value["type"] != kind:
        raise Invalid(path, message=f"Expected {kind} GeoJSON with coordinates only.")
    polys = value["coordinates"] if multi else [value["coordinates"]]
    if not isinstance(polys, list) or not 1 <= len(polys) <= 100:
        raise Invalid(path)
    count = 0
    for rings in polys:
        if not isinstance(rings, list) or not 1 <= len(rings) <= 100:
            raise Invalid(path)
        for ring in rings:
            if not isinstance(ring, list) or not 4 <= len(ring) <= 5000 or ring[0] != ring[-1]:
                raise Invalid(path, message="Rings must be explicitly closed, with 4–5000 positions.")
            count += len(ring)
            if count > 10000:
                raise Invalid(path, message="Geometry exceeds 10000 positions.")
            for point in ring:
                if not isinstance(point, list) or len(point) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not -180 <= x <= 180 or not math.isfinite(x) for x in point):
                    raise Invalid(path)
                if not -180 <= point[0] <= 180 or not -90 < point[1] < 90:
                    raise Invalid(path)
            if any(abs(a[0] - b[0]) >= 180 for a, b in zip(ring, ring[1:])):
                raise Invalid(path, message="Antimeridian-spanning edges are unsupported; split the geometry explicitly.")
    geom = shape(value)
    if not geom.is_valid:
        reason = explain_validity(geom)
        raise Invalid(path, "self_intersecting" if "intersection" in reason.lower() else "invalid_topology", "Invalid polygon topology.")
    if geom.is_empty or geom.area <= 0 or geom.bounds[2] - geom.bounds[0] >= 180:
        raise Invalid(path)
    return geom


def metrics(geom):
    area, _ = GEOD.geometry_area_perimeter(orient(geom, sign=1.0))
    # Perimeter includes all boundaries, including holes.
    perimeter = GEOD.geometry_length(geom.boundary)
    return abs(area), perimeter


def field_data(data, boundary=None):
    allowed = {"name", "geometry", "excludedZones", "soilType", "soilPh", "cropType", "irrigation", "autoSpacing"}
    if not isinstance(data, dict) or set(data) - allowed or not {"name", "geometry"} <= set(data):
        raise Invalid("body")
    result = {"excludedZones": None, "soilType": None, "soilPh": None, "cropType": None, "irrigation": "none", "autoSpacing": False, **data}
    for key in ("name", "soilType", "cropType"):
        v = result[key]
        if (key == "name" or v is not None) and (not isinstance(v, str) or not v.strip() or len(v) > 120):
            raise Invalid(key)
    ph = result["soilPh"]
    if ph is not None and (isinstance(ph, bool) or not isinstance(ph, (float, int)) or not 0 <= ph <= 14 or not math.isfinite(ph)):
        raise Invalid("soilPh")
    if result["irrigation"] not in ("none", "drip", "sprinkler", "flood", "other"):
        raise Invalid("irrigation")
    if not isinstance(result["autoSpacing"], bool):
        raise Invalid("autoSpacing")
    geom = polygon(result["geometry"])
    if boundary is not None and not polygon(boundary, "boundary").covers(geom):
        raise Invalid("geometry", "outside_farm_boundary", "Field must be covered by the farm boundary.")
    area, perimeter = metrics(geom)
    excluded = result["excludedZones"]
    removed = 0
    if excluded is not None:
        zones = polygon(excluded, "excludedZones", multi=True)
        if not geom.contains_properly(zones):
            raise Invalid("excludedZones", "outside_field", "Exclusions must be strictly inside the field, disjoint from holes and boundaries.")
        removed = sum(metrics(p)[0] for p in zones.geoms)
    if area <= removed:
        raise Invalid("excludedZones")
    return dict(result, areaM2=area, netAreaM2=area-removed, perimeterM=perimeter)


def bulk_items(document):
    if not isinstance(document, dict):
        raise Invalid("body")
    if set(document) == {"items"}:
        items = document["items"]
    elif set(document) == {"type", "features"} and document["type"] == "FeatureCollection":
        features = document["features"]
        if not isinstance(features, list) or not 1 <= len(features) <= 100:
            raise Invalid("features")
        items = []
        for feature in features:
            if not isinstance(feature, dict) or set(feature) != {"type", "geometry", "properties"} or feature["type"] != "Feature" or not isinstance(feature["properties"], dict) or "geometry" in feature["properties"]:
                raise Invalid("features")
            items.append(dict(feature["properties"], geometry=feature["geometry"]))
    else:
        raise Invalid("body", message="Expected an items document or GeoJSON FeatureCollection.")
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise Invalid("items")
    return items
