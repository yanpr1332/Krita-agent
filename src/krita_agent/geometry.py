"""Reproducible geometry and pressure planning, independent of Krita."""
import math
from .protocol import TaskError, number, points


def cubic_bezier(p0, p1, p2, p3, count=40, pressure=(0.1, 0.85, 0.1)):
    """Sample a cubic curve with a smooth rise and fall of pressure."""
    if type(count) is not int or not 2 <= count <= 2048:
        raise TaskError("count must be between 2 and 2048")
    if len(pressure) != 3:
        raise TaskError("pressure requires three values")
    start, middle, end = [number(v, "pressure", 0, 1) for v in pressure]
    control = [tuple(number(v, "coordinate", -65536, 65536) for v in p) for p in (p0, p1, p2, p3)]
    if any(len(p) != 2 for p in control):
        raise TaskError("control points must be 2D")
    samples = []
    for i in range(count):
        t = i / (count - 1)
        inv = 1 - t
        weights = (inv**3, 3*inv*inv*t, 3*inv*t*t, t**3)
        x = sum(w * p[0] for w, p in zip(weights, control))
        y = sum(w * p[1] for w, p in zip(weights, control))
        if t < .5:
            s = 2*t
            ease = s*s*(3-2*s)
            force = start + (middle-start)*ease
        else:
            s = 2*(t-.5)
            ease = s*s*(3-2*s)
            force = middle + (end-middle)*ease
        samples.append({"x": round(x, 4), "y": round(y, 4),
                        "pressure": round(force, 4), "time_ms": i * 16})
    return points(samples)


def demo_task():
    """Deterministic, editable multi-layer pressure-stroke sample."""
    return {
        "document": {"width": 1024, "height": 1024, "name": "Krita Agent Demo"},
        "layers": [
            {"name": "Structure", "brush": {"size": 10, "color": "#305070"},
             "strokes": [
                 {"shape": "rectangle", "rect": [80, 90, 860, 830]},
                 {"shape": "ellipse", "rect": [670, 160, 180, 180]},
                 {"points": cubic_bezier((100, 650), (280, 330), (620, 840), (910, 510), 54)}]},
            {"name": "Pressure Samples", "brush": {"size": 32, "color": "#B15A43",
             "pressure_enabled": True}, "strokes": [
                 {"points": cubic_bezier((110, 820), (300, 660), (520, 950), (900, 790), 60)},
                 {"points": cubic_bezier((110, 900), (340, 760), (610, 980), (920, 900), 60,
                                         pressure=(.7, .7, .7))}]},
            {"name": "Details", "brush": {"size": 8, "color": "#314B42"},
             "strokes": [{"shape": "polygon", "points": [
                 {"x": 440, "y": 400}, {"x": 590, "y": 270}, {"x": 740, "y": 430}]}]}
        ],
        "output": {"kra": "demo/krita-agent-demo.kra", "png": "demo/krita-agent-demo.png"}
    }
