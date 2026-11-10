"""Natural-language-to-ScenePlan v3 using an explicit JSON model provider."""
from .protocol import TaskError, label
from .scene_v3 import validate_scene, compile_scene_v3, digest

DIRECTOR_SYSTEM = """You are a visual creative director and Krita scene planner.
Return ONLY a JSON object conforming to schema krita-agent-scene/3.
All drawing must be generated as native Krita brush strokes on independently
editable layers, NOT copied/pasted images or a flat generated bitmap.
Scene keys: schema, document {width,height,name}, style, objects.
Objects: id (unique lowercase identifier), name, kind, bounds [x,y,w,h] in
canvas pixels, depth 0..1, optional parent id, brush {color:"#RRGGBB",
size:positive_number, opacity:0..1, optional preset}, optional min_strokes,
optional styles (a palette of named stroke-style objects), and elements.
Do not paint an entire object with one fixed color, size and pressure shape.
For each material, plan coarse volumetric strokes, medium contour/color strokes,
fine details and irregular accents. For example a cloud needs soft broad washes,
broken mid-size shadow planes and narrow lit edges; water needs ripples whose
length, spacing, lightness and direction change with perspective.
A style entry may contain brush {color,size,opacity,preset,pressure_enabled},
pressure_curve:[[0,0.2],[0.25,0.75],[0.6,0.9],[1,0.1]],
pressure_variation:0..0.3, variation_frequency:0.25..32,
variation_seed:nonnegative_integer, speed_sensitivity:0..1.
A stroke element can select style:"style_name" and override brush fields.
Each object MUST contain original native strokes:
{kind:"stroke",style:"wash",points:[{x,y,time_ms,speed},...]},
optionally {kind:"bezier",controls:[[x,y],[x,y],[x,y],[x,y]],samples:48,
style:"detail"}. Point pressure can be explicit; a stroke pressure_curve
overrides point pressure with a deterministic arc-length curve.
Vary colors and brush sizes BETWEEN strokes; Krita does not accept arbitrary
color changes inside one continuous native stroke. Choose actual meaningful
irregular contours, lighting planes and textures, not uniform parallel marks.
Keep all points on canvas, with correct horizon, depth, spatial relations and
material-specific detail density. Use 1..32 objects, 1..900 elements per object,
no more than 6000 total elements, and below 10000 compiled native steps.
For complex full landscapes, at least eight materially contributing objects.
Avoid user-identifying data, paths, arbitrary commands, code, plugin requests
or downloading assets. These are PROPOSALS, never completed artwork."""

def validate_brief(brief):
    if isinstance(brief, str):
        brief = {"prompt": brief}
    if not isinstance(brief, dict):
        raise TaskError("Creative brief must be text or a JSON object")
    prompt = brief.get("prompt")
    if not isinstance(prompt, str) or not 10 <= len(prompt.strip()) <= 5000:
        raise TaskError("Creative brief prompt must contain 10..5000 characters")
    width = brief.get("width", 1600)
    height = brief.get("height", 900)
    if type(width) is not int or type(height) is not int:
        raise TaskError("Canvas dimensions must be integers")
    if not 256 <= width <= 8192 or not 256 <= height <= 8192 or width * height > 32000000:
        raise TaskError("Creative canvas exceeds bounds")
    return {
        "prompt": prompt.strip(),
        "width": width,
        "height": height,
        "style": label(brief.get("style", "illustration"), "style", 160),
        "title": label(brief.get("title", "Creative Workflow"), "title", 120),
    }


def propose(brief, provider, reference_image=None):
    """Real provider call, no synthetic offline fallback pretending to be AI."""
    spec = validate_brief(brief)
    prompt = (
        "Create a complete editable scene matching this user brief. "
        "Canvas width={width}, height={height}, title={title}, style={style}.\n"
        "User request: {prompt}\n"
        "Return an original scene with irregular meaningful brush strokes "
        "with several scale/color/opacity choices per complex object, "
        "different pressure dynamics and varied irregular detail density, "
        "not a shallow geometric test or a few broad passes."
    ).format(**spec)
    inputs = [reference_image] if reference_image else []
    if reference_image:
        prompt += "\nA reference image is supplied as a complexity target. Do NOT paste it as the painting."
    candidate = provider.complete_json(DIRECTOR_SYSTEM, prompt, image_paths=inputs)
    scene = validate_scene(candidate)
    if scene["document"]["width"] != spec["width"] or scene["document"]["height"] != spec["height"]:
        raise TaskError("Model changed required canvas dimensions")
    return {
        "schema": "krita-agent-creative-proposal/1",
        "scene": scene,
        "scene_sha256": digest(scene),
        "provider_model": getattr(provider, "model", "externally_provided"),
        "approval": "required",
        "side_effects": "none; model proposal must be inspected",
    }


def compile_approved(proposal, profile_directory=None, build=None, preview_prefix=None):
    if not isinstance(proposal, dict) or proposal.get("schema") != "krita-agent-creative-proposal/1":
        raise TaskError("Unknown creative proposal format")
    scene = validate_scene(proposal.get("scene"))
    if digest(scene) != proposal.get("scene_sha256"):
        raise TaskError("Creative proposal content changed after planning")
    return compile_scene_v3(scene, profile_directory, build, preview_prefix)
