"""Semantic visual critique using actual rendered pixels and an explicit VLM.

This is iterative CREATIVE feedback, never independent final artwork
acceptance. Passing this critic does not create a human/VLM acceptance record.
"""
import hashlib
from pathlib import Path

from .model_provider import image_payload
from .scene_v3 import validate_scene
from .protocol import TaskError, number

SCHEMA = "krita-agent-creative-critique/1"

SYSTEM = """You are a visual art critic reviewing an ACTUAL Krita PNG supplied as pixels.
Never infer quality from a scene plan, filenames, logs, command counts or named
layers. Report obvious shape repetition, cloud volume, mountains, reflections,
composition, missing objects, inconsistent light, unfinished regions or
unintended clipping. Return ONLY JSON:
{
 "decision":"pass"|"needs_revision"|"insufficient_evidence",
 "observations":"Detailed observations of visible artwork",
 "issues":[{
   "object_id":"id from semantic scene",
   "severity":"minor"|"major"|"critical",
   "region":[x,y,width,height],
   "observation":"Concrete visible flaw in supplied image",
   "recommendation":"Specific localized painted improvement"
 }]
}
No claims about actual KRA editability or human acceptance.
Do not hallucinate unseen images or claim to have inspected a region not supplied.
Do not offer paste/composite of the reference as a solution."""

def _image_sha(path):
    item = Path(path).expanduser().resolve()
    if not item.is_file():
        raise TaskError("Actual exported artwork PNG is missing")
    return hashlib.sha256(item.read_bytes()).hexdigest()


def _issue(candidate, objects, width, height, index):
    if not isinstance(candidate, dict):
        raise TaskError("Critic issue must be an object")
    object_id = candidate.get("object_id")
    if object_id not in objects:
        raise TaskError("Critic issue refers to unknown object")
    severity = candidate.get("severity")
    if severity not in ("minor", "major", "critical"):
        raise TaskError("Invalid critic severity")
    box = candidate.get("region")
    if not isinstance(box, list) or len(box) != 4:
        raise TaskError("Critic issue requires a region")
    x, y, w, h = [number(v, "critic region", 0, max(width, height)) for v in box]
    if w <= 0 or h <= 0 or x + w > width or y + h > height:
        raise TaskError("Critic region must remain on canvas")
    text = candidate.get("observation")
    recommendation = candidate.get("recommendation")
    if not isinstance(text, str) or len(text.strip()) < 20:
        raise TaskError("Critic observation lacks concrete detail")
    if not isinstance(recommendation, str) or len(recommendation.strip()) < 15:
        raise TaskError("Critic recommendation is incomplete")
    return {
        "id": "issue-" + str(index + 1),
        "object_id": object_id,
        "severity": severity,
        "region": [x, y, w, h],
        "observation": text.strip()[:1200],
        "recommendation": recommendation.strip()[:1200],
    }


def critique(scene, artwork_png, provider, reference=None, max_round=3, round_index=1):
    spec = validate_scene(scene)
    if type(max_round) is not int or not 1 <= max_round <= 5:
        raise TaskError("Critique supports 1..5 rounds")
    if type(round_index) is not int or not 1 <= round_index <= max_round:
        raise TaskError("Critique round outside configured limit")
    from PIL import Image
    with Image.open(artwork_png) as im:
        if im.size != (spec["document"]["width"], spec["document"]["height"]):
            raise TaskError("Actual PNG dimensions differ from planned canvas")
        im.verify()
    observed_artwork = image_payload(artwork_png)
    ref = image_payload(reference) if reference is not None else None
    object_description = [
        {"id": obj["id"], "kind": obj["kind"], "bounds": obj["bounds"]}
        for obj in spec["objects"]
    ]
    import json
    prompt = (
        "Image 1 is the actual artwork, never a mockup. "
        + ("Image 2 is a complexity-only reference, not a pixel target. " if ref else "")
        + "Check each semantic object against actual pixels. "
        + "Scene objects (for identification, NOT visual proof): "
        + json.dumps(object_description, ensure_ascii=False)
        + "\nReturn grounded localized issues. Round {} of {}.".format(round_index, max_round)
    )
    inputs = [artwork_png] + ([reference] if reference else [])
    output = provider.complete_json(SYSTEM, prompt, image_paths=inputs)
    decision = output.get("decision")
    if decision not in ("pass", "needs_revision", "insufficient_evidence"):
        raise TaskError("Critic decision is invalid")
    observation = output.get("observations")
    if not isinstance(observation, str) or len(observation.strip()) < 30:
        raise TaskError("Critic must describe the actual image")
    raw = output.get("issues")
    if not isinstance(raw, list) or len(raw) > 20:
        raise TaskError("Critic supports up to 20 localized issues")
    objects = {o["id"] for o in spec["objects"]}
    issues = [_issue(row, objects, spec["document"]["width"],
                     spec["document"]["height"], i) for i, row in enumerate(raw)]
    if (decision == "pass" and issues) or (decision == "needs_revision" and not issues):
        raise TaskError("Critic decision and issues contradict")
    return {
        "schema": SCHEMA,
        "model": getattr(provider, "model", "external"),
        "artwork_png_sha256": observed_artwork["sha256"],
        "reference_sha256": ref["sha256"] if ref else None,
        "round": round_index, "max_rounds": max_round,
        "decision": decision,
        "observations": observation.strip()[:4000],
        "issues": issues,
        "side_effects": "none; human review required before revisions",
        "independent_artwork_acceptance": False,
    }
