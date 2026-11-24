"""Read-only native-stroke join risk audit for a specific Krita build.

This is capability and compiled-command analysis, NOT a measurement of
the rendered stroke. Stable Krita builds that lack paintPolylineStroke
must not silently be credited with native-continuous stroke behavior.
"""
from .protocol import TaskError

SCHEMA = "krita-agent-native-continuity/1"
MAX_EXAMPLES = 20


def inspect_stroke_continuity(steps, capabilities):
    """Predict *possible* segmented join deposits before native submission.

    Auto uses the continuous path only when both native symbols are present.
    Two-point paintLine strokes have no *interior* segment join. An explicit
    segmented mode with >=3 points always has such joins, even on Next builds.

    This audit cannot determine whether a brush actually deposits extra alpha,
    or whether its pressure curve is responsive; those require real pixels.
    """
    if not isinstance(steps, list):
        raise TaskError("Native stroke audit requires a compiled step list")
    if not isinstance(capabilities, dict):
        raise TaskError("Native Krita capabilities are unavailable")
    symbols = capabilities.get("symbols")
    if not isinstance(symbols, dict):
        raise TaskError("Native Krita symbol inventory is unavailable")
    available = (symbols.get("Node.paintPolylineStroke") is True
                 and symbols.get("StrokePoint") is True)
    risks = []
    scanned = 0
    blocked = 0
    unsupported = 0
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise TaskError("Malformed compiled native step")
        if step.get("command") != "draw.stroke":
            continue
        params = step.get("parameters")
        if not isinstance(params, dict):
            raise TaskError("Malformed compiled stroke parameters")
        mode = params.get("mode", "auto")
        pts = params.get("points")
        if mode not in ("auto", "continuous", "segmented"):
            raise TaskError("Unknown compiled native stroke mode")
        if not isinstance(pts, list) or not 1 <= len(pts) <= 2048:
            raise TaskError("Malformed compiled stroke points")
        scanned += 1
        # Even one explicitly continuous stroke cannot execute without API.
        cannot_execute = mode == "continuous" and not available
        # Multiple separate paintLine calls will touch the same interior
        # endpoints; the rendered deposit depends on the selected brush.
        segmented = mode == "segmented" or (mode == "auto" and not available)
        join_risk = segmented and len(pts) >= 3
        if cannot_execute:
            unsupported += 1
        if join_risk:
            blocked += 1
        if (cannot_execute or join_risk) and len(risks) < MAX_EXAMPLES:
            risks.append({
                "step_index": index,
                "mode": mode,
                "points": len(pts),
                "reason": ("continuous_api_missing" if cannot_execute
                           else "interior_segmented_joins"),
            })
    return {
        "schema": SCHEMA,
        "build": {
            "krita_version": capabilities.get("krita_version"),
            "qt_version": capabilities.get("qt_version"),
            "qt_binding": capabilities.get("qt_binding"),
        },
        "continuous_symbols_present": available,
        "continuous_visual_response_verified": False,
        "draw_strokes_scanned": scanned,
        "segmented_join_risk_strokes": blocked,
        "unsupported_continuous_strokes": unsupported,
        "examples": risks,
        "examples_truncated": blocked + unsupported > len(risks),
        "reject_segmented_joins_preflight_passed": not blocked and not unsupported,
        "artwork_accepted": False,
        "note": (
            "Read-only symbol/path analysis; actual alpha joins, preset "
            "pressure and artwork quality require native pixel inspection"
        ),
    }


def reject_unsafe_segmented_joins(steps, capabilities):
    """Fail *before* native submission when a caller opts into no join risk."""
    result = inspect_stroke_continuity(steps, capabilities)
    if not result["reject_segmented_joins_preflight_passed"]:
        raise TaskError(
            "Native stroke preflight blocked: {} segmented join risk(s), "
            "{} unsupported continuous stroke(s); inspect capabilities "
            "or choose an explicitly accepted legacy drawing path".format(
                result["segmented_join_risk_strokes"],
                result["unsupported_continuous_strokes"],
            )
        )
    return result
