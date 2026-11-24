"""Round 16 deterministic, purpose-driven native stroke point generator.

No artificial image, fake pen sensor, brush engine override or Krita command.
This outputs bounded XY/pressure/time samples for the EXISTING draw.stroke
allowlist. Physical stylus and real preset response remain to be tested.
"""
import math

from .protocol import TaskError, number, integer, points

SCHEMA = "krita-agent-natural-stroke/1"
PURPOSES = frozenset(("contour", "fine_detail", "fur", "fold", "vegetation"))
MAX_SAMPLES = 2048
PROFILE = {
    "contour": (0.16, 0.80, 0.18),
    "fine_detail": (0.10, 0.60, 0.10),
    "fur": (0.24, 0.84, 0.04),
    "fold": (0.12, 0.76, 0.09),
    "vegetation": (0.20, 0.78, 0.06),
}


def validate_natural(raw):
    if type(raw) is not dict:
        raise TaskError("Natural stroke specification must be an object")
    allowed = {"purpose", "spacing", "smoothing_passes",
               "start_pressure", "peak_pressure", "end_pressure",
               "corner_relief"}
    extra = set(raw)-allowed
    if extra:
        raise TaskError("Unsupported natural stroke fields: " +
                        ", ".join(sorted(extra)))
    purpose = raw.get("purpose", "contour")
    if purpose not in PURPOSES:
        raise TaskError("Unsupported natural stroke purpose")
    start, peak, end = PROFILE[purpose]
    start = number(raw.get("start_pressure", start), "start_pressure", 0.02, 1)
    peak = number(raw.get("peak_pressure", peak), "peak_pressure", 0.02, 1)
    end = number(raw.get("end_pressure", end), "end_pressure", 0.02, 1)
    if peak < max(start, end):
        raise TaskError("Natural peak pressure must be >= end pressures")
    return {
        "purpose": purpose,
        "spacing": number(raw.get("spacing", 4), "stroke spacing", .75, 24),
        "smoothing_passes": integer(raw.get("smoothing_passes", 1),
                                     "smoothing passes", 0, 2),
        "start_pressure": start,
        "peak_pressure": peak,
        "end_pressure": end,
        "corner_relief": number(raw.get("corner_relief", .18),
                                "corner relief", 0, .4),
    }


def _length(a, b):
    return math.hypot(b[0]-a[0], b[1]-a[1])


def _chaikin(raw):
    """Preserve first/last and make each new point a convex combination."""
    result = [raw[0]]
    for a, b in zip(raw, raw[1:]):
        result.append((.75*a[0]+.25*b[0], .75*a[1]+.25*b[1]))
        result.append((.25*a[0]+.75*b[0], .25*a[1]+.75*b[1]))
    result.append(raw[-1])
    return result


def _angle(prev, here, nxt):
    a = (here[0]-prev[0], here[1]-prev[1])
    b = (nxt[0]-here[0], nxt[1]-here[1])
    la, lb = math.hypot(*a), math.hypot(*b)
    if la < 1e-7 or lb < 1e-7:
        return 0.
    dot = max(-1., min(1., (a[0]*b[0]+a[1]*b[1])/(la*lb)))
    return math.acos(dot)


def _smoothstep(value):
    t = max(0., min(1., value))
    return t*t*(3-2*t)


def natural_points(path, settings, bounds):
    """Return deterministic, tapered, curve-aware, bounded native samples.

    path: validated sequence of [x,y] coordinates in approved subject bbox.
    settings: strictly validated purpose and bounded tuning.
    bounds: [x,y,width,height] in pixel coordinates.
    Endpoints and original order are preserved; all intermediate positions
    stay in the convex hull of the supplied guides. No hidden random noise.
    """
    profile = validate_natural(settings)
    if type(bounds) is not list or len(bounds) != 4:
        raise TaskError("Native natural stroke needs an approved subject bbox")
    bx, by, bw, bh = bounds
    for value in bounds:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise TaskError("Natural stroke bounds must be finite")
    if bx < 0 or by < 0 or bw <= 0 or bh <= 0:
        raise TaskError("Natural stroke bbox is invalid")
    if not isinstance(path, list) or not 2 <= len(path) <= 128:
        raise TaskError("Natural stroke needs 2..128 guide points")
    raw = []
    for pt in path:
        if type(pt) is not list or len(pt) != 2:
            raise TaskError("Natural stroke point must be [x,y]")
        x, y = pt
        if (type(x) not in (int, float) or type(y) not in (int, float)
                or not math.isfinite(x) or not math.isfinite(y)
                or not bx <= x <= bx+bw or not by <= y <= by+bh):
            raise TaskError("Natural stroke guide leaves its approved bbox")
        if raw and (x, y) == raw[-1]:
            raise TaskError("Consecutive duplicate natural stroke guides")
        raw.append((float(x), float(y)))
    if not any(_length(a, b) > 1e-6 for a, b in zip(raw, raw[1:])):
        raise TaskError("Natural stroke guide is degenerate")

    control = raw
    for _ in range(profile["smoothing_passes"]):
        control = _chaikin(control)
        if len(control) > MAX_SAMPLES:
            raise TaskError("Natural stroke smoothing exceeds sample budget")

    # Adaptive non-overshooting sampling; sharper local turns require more
    # points, but not artificially increased pressure or random zigzags.
    sampled = [control[0]]
    for i, (a, b) in enumerate(zip(control, control[1:])):
        left = control[max(0, i-1)]
        right = control[min(len(control)-1, i+2)]
        turning = max(_angle(left, a, b), _angle(a, b, right))
        spacing = profile["spacing"] / (1. + 1.5*turning/math.pi)
        count = max(1, math.ceil(_length(a, b)/spacing))
        if len(sampled)+count > MAX_SAMPLES:
            raise TaskError("Natural stroke exceeds 2048 native samples")
        for j in range(1, count+1):
            t = j/count
            sampled.append((a[0]+(b[0]-a[0])*t,
                            a[1]+(b[1]-a[1])*t))
    # Remove numerical duplicates, but retain the actual last endpoint.
    clean = [sampled[0]]
    for p in sampled[1:]:
        if _length(clean[-1], p) > 1e-7:
            clean.append(p)
    if len(clean) < 2 or len(clean) > MAX_SAMPLES:
        raise TaskError("Natural stroke has too few or too many visible points")
    lengths = [0.]
    for a, b in zip(clean, clean[1:]):
        lengths.append(lengths[-1]+_length(a, b))
    total = lengths[-1]
    if total < 1e-5:
        raise TaskError("Natural stroke has negligible length")
    result = []
    start, peak, end = (profile[k] for k in (
        "start_pressure", "peak_pressure", "end_pressure"))
    for i, ((x, y), arclength) in enumerate(zip(clean, lengths)):
        t = arclength/total
        onset = _smoothstep(t/.18)
        release = _smoothstep((1.-t)/.20)
        envelope = min(onset, release)
        baseline = (start if t <= .5 else end)
        pressure = baseline+(peak-baseline)*envelope
        if 0 < i < len(clean)-1:
            curve = _angle(clean[i-1], clean[i], clean[i+1])
            pressure *= (1-profile["corner_relief"]*curve/math.pi)
        result.append({
            "x": round(max(bx, min(bx+bw, x)), 4),
            "y": round(max(by, min(by+bh, y)), 4),
            "pressure": round(max(.02, min(1., pressure)), 6),
            "time_ms": i*16,
            "speed": .5,
        })
    # Protocol validates every sensor, bound and time coordinate once more.
    return points(result)
