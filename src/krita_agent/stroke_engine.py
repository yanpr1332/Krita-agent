"""Offline stroke planner: smoothing, equal-distance sampling, pressure interpolation.

All output is validated in the shared JSON protocol before reaching Krita.
Continuous native drawing is preferred where runtime capability permits it.
"""
import math
from .protocol import TaskError, points


def _interp(a, b, t):
    return {key: a[key] + (b[key]-a[key])*t
            for key in ("x", "y", "pressure", "time_ms", "x_tilt",
                        "y_tilt", "rotation", "speed", "tangential_pressure")}


def _distance(a, b):
    return math.hypot(b["x"]-a["x"], b["y"]-a["y"])


def resample(samples, spacing=3.0, max_points=2048):
    """Preserve endpoints, timestamps and sensors while resampling by arc length."""
    path = points(samples)
    if type(spacing) not in (int, float) or not math.isfinite(spacing) or not 0.5 <= spacing <= 100:
        raise TaskError("spacing must be in [0.5,100]")
    if type(max_points) is not int or not 2 <= max_points <= 2048:
        raise TaskError("max_points outside 2..2048")
    if len(path) == 1:
        return path
    cumulative = [0.0]
    for i in range(1, len(path)):
        cumulative.append(cumulative[-1]+_distance(path[i-1], path[i]))
    length = cumulative[-1]
    if length == 0:
        return [path[0], path[-1]]
    count = min(max_points, max(2, math.ceil(length/spacing)+1))
    output = []
    segment = 1
    for index in range(count):
        target = length*index/(count-1)
        while segment < len(cumulative)-1 and cumulative[segment] < target:
            segment += 1
        before, after = cumulative[segment-1], cumulative[segment]
        fraction = (target-before)/(after-before) if after > before else 0
        output.append(_interp(path[segment-1], path[segment], fraction))
    output[0], output[-1] = path[0], path[-1]
    return points(output)


def smooth(samples, passes=2, strength=0.4):
    """Laplacian smoothing of interior XY positions; preserve pressure and endpoints."""
    path = points(samples)
    if type(passes) is not int or not 0 <= passes <= 10:
        raise TaskError("passes out of range")
    if type(strength) not in (int, float) or not math.isfinite(strength) or not 0 <= strength <= 1:
        raise TaskError("strength out of range")
    for _ in range(passes):
        result = [dict(p) for p in path]
        for i in range(1, len(path)-1):
            for dim in ("x", "y"):
                average = (path[i-1][dim]+path[i+1][dim])/2
                result[i][dim] = path[i][dim]*(1-strength)+average*strength
        path = result
    return points(path)


def catmull_rom(control, samples_per_segment=8, tension=0.5):
    """Convert an ordered control-point path to cubic Hermite samples.

    Handles all supported stroke sensors by interpolating the corresponding
    scalar values; resampling must still be requested separately if desired.
    """
    control = points(control)
    if len(control) < 2:
        raise TaskError("Two control points required")
    if type(samples_per_segment) is not int or not 2 <= samples_per_segment <= 64:
        raise TaskError("samples_per_segment out of range")
    if type(tension) not in (int, float) or not 0 <= tension <= 1:
        raise TaskError("tension out of range")
    expected = (len(control)-1)*samples_per_segment+1
    if expected > 2048:
        raise TaskError("Spline would exceed maximum 2048 points")
    result = []
    dims = ("x", "y", "pressure", "time_ms", "x_tilt", "y_tilt",
            "rotation", "speed", "tangential_pressure")
    for i in range(len(control)-1):
        p0 = control[max(0, i-1)]
        p1, p2 = control[i], control[i+1]
        p3 = control[min(len(control)-1, i+2)]
        for step in range(samples_per_segment):
            t = step / samples_per_segment
            # Hermite basis with positive derivatives; may overshoot slightly.
            h0, h1 = 2*t**3-3*t*t+1, t**3-2*t*t+t
            h2, h3 = -2*t**3+3*t*t, t**3-t*t
            sample = {}
            for dim in dims:
                m1 = (p2[dim]-p0[dim])*tension
                m2 = (p3[dim]-p1[dim])*tension
                value = h0*p1[dim]+h1*m1+h2*p2[dim]+h3*m2
                if dim in ("pressure", "speed", "tangential_pressure"):
                    value = max(0, min(1, value))
                if dim == "time_ms":
                    value = max(p1[dim], min(p2[dim], value))
                if dim in ("x_tilt", "y_tilt"):
                    value = max(-90, min(90, value))
                sample[dim] = value
            result.append(sample)
    result.append(control[-1])
    return points(result)


def plan_stroke(spec):
    """Compile a stroke with optional spline, smoothing, and spatial resampling."""
    if not isinstance(spec, dict):
        raise TaskError("stroke spec must be an object")
    result = points(spec.get("points", []))
    if spec.get("spline", False):
        result = catmull_rom(result, spec.get("samples_per_segment", 8),
                            spec.get("tension", 0.5))
    if spec.get("smooth", False):
        result = smooth(result, spec.get("smoothing_passes", 2),
                        spec.get("smoothing_strength", 0.4))
    if "spacing" in spec:
        result = resample(result, spec["spacing"])
    return result
