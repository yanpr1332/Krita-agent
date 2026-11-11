"""Opt-in generalist staged creative direction; models describe paint intent.

The provider never receives direct Krita command authority or permission to
write native files. Its JSON must be validated and lowered before approval.
"""
from .creative_director import validate_brief
from .protocol import TaskError
from .scene_v3 import digest
from .scene_v4 import compile_scene_v4, validate_scene_v4

GENERALIST_SYSTEM = """You are a generalist painting director preparing an
original editable Krita painting. Output ONLY one JSON object with schema
krita-agent-scene/4. Never output executable code, external filenames, arbitrary
commands, reference-image pastes, or a hardcoded benchmark-specific painting.
Plan composition and stages rather than listing thousands of pen coordinates.

Top-level: schema, document:{width,height,name}, style, subjects, stages.
subjects is 1..24 objects with:
{id:"figure",name:"Standing person",kind:"person",materials:["skin","cloth"],
bounds:[x,y,width,height],depth:0.5,optional parent:"other-subject-id",
brush:{color:"#RRGGBB",size:12,opacity:0.8},
optional styles:{"contour":{"brush":{"size":4,"color":"#332222"},
"pressure_curve":[[0,0.1],[0.45,0.9],[1,0.1]]}}}.
Subject kind is free descriptive text: human, animal, building, vessel, sky,
hair, shirt, bicycle etc. Material is separate from semantic subject.

stages contains 3..6 ordered items chosen from phases
sketch, block_in, form, material, detail, polish. FIRST must be sketch,
LAST detail or polish. Each item has:
{id:"sketch",phase:"sketch",goal:"Establish proportions and silhouettes",
intents:[ ...1..32 high-level paint actions... ]}.
An intent requires id, subject_id, kind and meaningful purpose:
- gesture: path:[[x,y],[x,y],...] (2..128 points) for outlines/gesture.
- coverage: polygon:[[x,y],...>=3] with spacing:1..200 and angle:-180..180;
  generates real brush fill strokes clipped to the polygon (not a pasted image).
- accents: path:[[x,y],...], count:1..64, length:1..200; yields localized marks.
Optional material (must be among subject materials), style (subject palette),
brush:{size,color,opacity,preset,pressure_enabled},
pressure_curve:[[0,value],[1,value]], jitter:0..0.25, seed:nonnegative integer.
Coordinates must be within the SUBJECT bounds and the canvas. For each
intent, state WHY those marks are needed in purpose (structure, volume,
lighting, anatomy, edge or detail). Keep stage intent counts manageable,
and let the deterministic Krita-native compiler expand geometry.
Do not plan by repetitive line-count targets. Include plausible
relationships, proportions, perspective and occlusion for the specific
subject matter. Do not claim a painting has been rendered.
No authorization for actual drawing is provided by this proposal.
"""


def propose_generalist(brief, provider, reference_image=None):
    spec = validate_brief(brief)
    prompt = (
        "Create a coherent generalist staged painting plan for canvas "
        "{width} x {height}, named {title}, style {style}. "
        "User brief: {prompt}. Plan structural proportions, color block-in "
        "and purposeful later details across 3..6 stages. "
        "Do not enumerate low-level pen points for the full painting."
    ).format(**spec)
    images = [reference_image] if reference_image else []
    if reference_image:
        prompt += (
            " A user-supplied reference is available for composition/complexity. "
            "Analyze its visible content, do not paste its pixels as artwork."
        )
    candidate = provider.complete_json(GENERALIST_SYSTEM, prompt,
                                       image_paths=images)
    scene = validate_scene_v4(candidate)
    if (scene["document"]["width"], scene["document"]["height"]) != (
            spec["width"], spec["height"]):
        raise TaskError("Generalist model changed approved canvas dimensions")
    return {
        "schema": "krita-agent-generalist-proposal/1",
        "scene_v4": scene, "scene_v4_sha256": digest(scene),
        "provider_model": getattr(provider, "model", "externally_provided"),
        "approval": "required",
        "side_effects": "none; stage-by-stage native drawing requires approval",
    }


def compile_approved_generalist(proposal, profile_directory=None, build=None,
                                preview_prefix=None):
    if (not isinstance(proposal, dict) or
            proposal.get("schema") != "krita-agent-generalist-proposal/1"):
        raise TaskError("Unknown generalist proposal format")
    scene = validate_scene_v4(proposal.get("scene_v4"))
    if digest(scene) != proposal.get("scene_v4_sha256"):
        raise TaskError("Generalist proposal changed after planning")
    return compile_scene_v4(scene, profile_directory, build, preview_prefix)
