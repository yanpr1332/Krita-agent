"""Round 15: read-only audit of genuine native Krita region-fill needs.

Native Krita paintPolygon is a real editable layer operation. This module
checks symbol availability and compiled step intent, NOT actual colored pixels.
"""
from .protocol import TaskError

SCHEMA = "krita-agent-native-regions/1"
MAX_EXAMPLES = 24


def _filled_polygon(step):
    if type(step) is not dict:
        raise TaskError("Malformed native region step")
    if step.get("command") != "draw.shape":
        return False
    params = step.get("parameters")
    if type(params) is not dict:
        raise TaskError("Malformed draw.shape parameters")
    return (params.get("shape") == "polygon" and
            params.get("fill") == "ForegroundColor")


def requires_native_regions(steps):
    if type(steps) is not list:
        raise TaskError("Native region audit needs native steps")
    return any(_filled_polygon(step) for step in steps)


def inspect_native_regions(steps, capabilities):
    """Distinguish presence of the native API from real fill acceptance."""
    if type(steps) is not list or type(capabilities) is not dict:
        raise TaskError("Native region capabilities or steps unavailable")
    symbols = capabilities.get("symbols")
    if type(symbols) is not dict:
        raise TaskError("Native region symbol inventory unavailable")
    indices = [i for i, step in enumerate(steps) if _filled_polygon(step)]
    available = symbols.get("Node.paintPolygon") is True
    return {
        "schema": SCHEMA,
        "build": {
            "krita_version": capabilities.get("krita_version"),
            "qt_version": capabilities.get("qt_version"),
            "qt_binding": capabilities.get("qt_binding"),
        },
        "filled_region_steps": len(indices),
        "required_symbol": "Node.paintPolygon",
        "symbol_present_in_build": available,
        "unsupported_region_steps": 0 if available else len(indices),
        "first_region_step_indices": indices[:MAX_EXAMPLES],
        "requires_actual_native_pixel_review": bool(indices),
        "real_native_region_verified": False,
        "artwork_accepted": False,
    }


def require_supported_regions(steps, capabilities):
    report = inspect_native_regions(steps, capabilities)
    if report["unsupported_region_steps"]:
        raise TaskError(
            "Native filled polygon stage requires Node.paintPolygon, "
            "which is absent from this Krita build")
    return report
