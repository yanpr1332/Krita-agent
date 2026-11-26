"""R17 deterministic light-aware, material-aware *region* paint planning.

This pure module constructs bounded clipped highlight/shadow polygons and
perceptually reasonable, non-identical light/value palettes. It does NOT infer
3D normals, pixels, photo-real shading or native brush preset behavior.
"""
import math
import re

from .protocol import TaskError

LIGHT_SCHEMA = "krita-agent-lighting/1"
DEFAULT_LIGHT = {
    "direction": [-0.6, -0.8],  # toward light source in canvas coordinates
    "strength": 0.56,
    "warmth": 0.20,
    "shadow_fraction": 0.35,
    "highlight_fraction": 0.22,
}
# Contrast response is an artistic heuristic, not physically based rendering.
MATERIAL_CONTRAST = {
    "metal": 1.40, "glass": 1.32, "ceramic": 1.05, "porcelain": 1.07,
    "skin": 0.74, "cloth": 0.72, "fabric": 0.72, "fur": 0.79,
    "wood": 0.89, "plant": 0.86, "leaf": 0.86, "water": 1.16,
    "stone": 0.84, "rock": 0.84, "paint": 0.88,
}
HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")


def _real(value, name, lo, hi):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise TaskError(name + " must be a finite number")
    if not lo <= value <= hi:
        raise TaskError(name + " is outside allowed bounds")
    return float(value)


def validate_lighting(raw=None):
    """Canonical, JSON-stable directional light; safe for revalidation."""
    if raw is None:
        raw = {}
    if type(raw) is not dict:
        raise TaskError("Lighting must be a JSON object")
    extra = set(raw) - set(DEFAULT_LIGHT) - {"schema"}
    if extra:
        raise TaskError("Unknown lighting fields: " + ", ".join(sorted(extra)))
    if "schema" in raw and raw["schema"] != LIGHT_SCHEMA:
        raise TaskError("Invalid lighting schema")
    direction = raw.get("direction", DEFAULT_LIGHT["direction"])
    if type(direction) is not list or len(direction) != 2:
        raise TaskError("Lighting direction must be [dx,dy]")
    dx, dy = [_real(v, "lighting direction", -1, 1) for v in direction]
    length = math.hypot(dx, dy)
    if length < .05:
        raise TaskError("Lighting direction must be nonzero")
    # Preserve already canonical unit vectors exactly; no round-trip drift.
    if abs(length-1) > 1e-6:
        dx, dy = round(dx/length, 6), round(dy/length, 6)
    result = {
        "schema": LIGHT_SCHEMA, "direction": [dx, dy],
        "strength": _real(raw.get("strength", DEFAULT_LIGHT["strength"]),
                          "light strength", 0, 1),
        "warmth": _real(raw.get("warmth", DEFAULT_LIGHT["warmth"]),
                        "light warmth", -1, 1),
        "shadow_fraction": _real(
            raw.get("shadow_fraction", DEFAULT_LIGHT["shadow_fraction"]),
            "shadow fraction", .1, .48),
        "highlight_fraction": _real(
            raw.get("highlight_fraction", DEFAULT_LIGHT["highlight_fraction"]),
            "highlight fraction", .08, .42),
    }
    if result["shadow_fraction"] + result["highlight_fraction"] > .85:
        raise TaskError("Light bands consume too much of the subject")
    return result


def _rgb(color):
    if type(color) is not str or HEX.fullmatch(color) is None:
        raise TaskError("Material base color must be #RRGGBB")
    return [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]


def _linear(value):
    return value/12.92 if value <= .04045 else ((value+.055)/1.055)**2.4


def _srgb(value):
    value = max(0.0, min(1.0, value))
    return 12.92*value if value <= .0031308 else 1.055*value**(1/2.4)-.055


def _mix_light(base, tint, amount):
    amount = max(0, min(.85, amount))
    linear = [(_linear(a)*(1-amount) + _linear(b)*amount)
              for a, b in zip(_rgb(base), tint)]
    return "#" + "".join("%02x" % round(255*_srgb(x)) for x in linear)


def _material_response(materials):
    if not isinstance(materials, list) or not materials:
        raise TaskError("Subject materials must be a nonempty list")
    for item in materials:
        if type(item) is not str or len(item) > 64:
            raise TaskError("Invalid subject material")
        lower = item.lower()
        for material, contrast in MATERIAL_CONTRAST.items():
            if material in lower:
                return contrast, material
    return .9, "generic"


def material_palette(base, materials, lighting):
    """Three distinct native foreground RGBs with warm/cool value separation."""
    light = validate_lighting(lighting)
    _rgb(base)
    response, category = _material_response(materials)
    strength = light["strength"]
    # Weathered/diffuse materials are softer; ceramic/metal are more specular.
    amount_shadow = min(.72, (.20+.24*strength)*response)
    amount_lit = min(.72, (.13+.29*strength)*response)
    warm = light["warmth"]
    highlight_tint = [max(0, min(1, x)) for x in
                      (.96+.03*warm, .95+.01*warm, .94-.08*warm)]
    shadow_tint = [max(0, min(1, x)) for x in
                   (.025+.02*warm, .038, .075-.015*warm)]
    base = base.lower()
    shadow = _mix_light(base, shadow_tint, amount_shadow)
    highlight = _mix_light(base, highlight_tint, amount_lit)
    return {
        "base": base, "shadow": shadow, "highlight": highlight,
        "material_profile": category,
        "native_rgb_changes_between_regions": True,
        "native_in_stroke_rgb_changes": False,
        "not_photorealistic": True,
    }


def _area(poly):
    return abs(sum(x*v-y*u for (x,y),(u,v) in
                   zip(poly, poly[1:]+poly[:1])))/2


def _intersection(a, b, direction, cutoff):
    da = a[0]*direction[0]+a[1]*direction[1]-cutoff
    db = b[0]*direction[0]+b[1]*direction[1]-cutoff
    denom = da-db
    if abs(denom) < 1e-12:
        return a
    t = max(0.0, min(1.0, da/denom))
    return (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))


def _clip_halfplane(poly, direction, cutoff, keep_high):
    out = []
    def inside(p):
        q = p[0]*direction[0]+p[1]*direction[1]-cutoff
        return q >= -1e-12 if keep_high else q <= 1e-12
    for prev, cur in zip(poly[-1:]+poly[:-1], poly):
        was, now = inside(prev), inside(cur)
        if was != now:
            out.append(_intersection(prev, cur, direction, cutoff))
        if now:
            out.append(cur)
    if len(out) < 3:
        return []
    # Remove consecutive repeats and collinear clipped edges. This avoids
    # false self-intersections in the strict v4 polygon gate.
    clean = []
    for p in out:
        if not clean or math.hypot(p[0]-clean[-1][0],
                                   p[1]-clean[-1][1]) > 1e-8:
            clean.append(p)
    if len(clean) > 1 and math.hypot(clean[0][0]-clean[-1][0],
                                     clean[0][1]-clean[-1][1]) <= 1e-8:
        clean.pop()
    changed = True
    while changed and len(clean) > 3:
        changed = False
        for i in range(len(clean)):
            a, b, c = clean[i-1], clean[i], clean[(i+1)%len(clean)]
            cross = (b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
            if abs(cross) < 1e-10:
                del clean[i]
                changed = True
                break
    return clean if len(clean) >= 3 and _area(clean) > 1e-10 else []


def light_regions(outline, colors, lighting, canvas):
    """Bounded geometries for base / darker side / illuminated side.

    Input outline is a *convex* normalized primitive from R14 (NOT user
    supplied arbitrary polygons); output is normalized local clips.
    Pixel coverage is checked later by ScenePlan v4's native region guard.
    """
    light = validate_lighting(lighting)
    if (type(canvas) is not list or len(canvas) != 2 or any(
            type(v) is not int or not 1 <= v <= 8192 for v in canvas)):
        raise TaskError("Lighting canvas must be [width,height]")
    if not isinstance(outline, list) or not 3 <= len(outline) <= 32:
        raise TaskError("Lighting requires a bounded convex primitive polygon")
    poly = []
    for p in outline:
        if (type(p) is not list or len(p) != 2 or
                any(type(v) not in (int, float) or
                    not math.isfinite(v) or not 0 <= v <= 1 for v in p)):
            raise TaskError("Lighting polygon leaves normalized canvas")
        poly.append((float(p[0]), float(p[1])))
    if _area(poly) <= 1e-10:
        raise TaskError("Lighting outline has insufficient area")
    dx, dy = light["direction"]
    # Project in PIXEL space to keep shape consistently illuminated even
    # on a tall/very wide canvas; projection is monotone in normalized form.
    axis = (dx*canvas[0], dy*canvas[1])
    projections = [x*axis[0]+y*axis[1] for x,y in poly]
    lo, hi = min(projections), max(projections)
    if hi-lo <= .5:
        raise TaskError("Lighting polygon has insufficient directional extent")
    high_cut = hi-light["highlight_fraction"]*(hi-lo)
    low_cut = lo+light["shadow_fraction"]*(hi-lo)
    output = [{"role": "base", "polygon": [[x,y] for x,y in poly],
               "color": colors["base"]}]
    for role, points in (
        ("shadow", _clip_halfplane(poly, axis, low_cut, False)),
        ("highlight", _clip_halfplane(poly, axis, high_cut, True)),
    ):
        if not points:
            continue
        rounded = [[round(x, 6), round(y, 6)] for x,y in points]
        # Avoid tiny degenerate fills in real canvas pixels (R15 rejects).
        if _area([tuple(p) for p in rounded])*canvas[0]*canvas[1] < 2.:
            continue
        output.append({"role": role, "polygon": rounded,
                       "color": colors[role]})
    return output
