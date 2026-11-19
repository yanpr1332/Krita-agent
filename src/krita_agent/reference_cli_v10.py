"""User-facing Round 10 reference & technique CLI; no implicit Krita draw/network."""
import json
from pathlib import Path

from .reference_assets_v10 import analyze_references
from .reference_plan_v10 import propose_reference_repaint, approve_reference_repaint
from .reference_compare_v10 import compare_native_repaint
from .technique_library_v10 import (
    save_technique, load_technique, list_techniques,
    propose_technique_application, approve_technique_application,
)


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _output(value, path):
    if not path:
        return value
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return {"written": str(target), "no_overwrite": True, "status": "proposed_or_reported",
            "native_effects": "none"}


def register(commands):
    entry = commands.add_parser("reference", help="Authorized reference analysis / techniques (Round 10)")
    actions = entry.add_subparsers(dest="reference_action", required=True)
    for name in ("analyze", "annotate", "propose", "approve", "compare", "technique-save",
                 "technique-list", "technique-plan", "technique-approve", "technique-extract"):
        p = actions.add_parser(name)
        if name not in ("technique-save", "technique-list", "technique-plan",
                        "technique-approve"):
            if name in ("analyze", "annotate", "approve", "technique-extract"):
                p.add_argument("--root", required=True, help="Authorized directory with image sources")
            if name in ("analyze", "approve", "technique-extract"):
                p.add_argument("--manifest", required=True)
            if name not in ("analyze", "annotate", "technique-extract"):
                p.add_argument("--scene", required=True)
            if name in ("propose", "compare"):
                p.add_argument("--analysis", required=True)
                p.add_argument("--bindings", required=True, help="JSON list of explicit source/ROI/subject mappings")
            if name == "technique-extract":
                p.add_argument("--source-id", required=True)
                p.add_argument("--region-id", required=True)
                p.add_argument("--id", required=True)
                p.add_argument("--version", type=int, default=1)
                p.add_argument("--material")
                p.add_argument("--phase", default="material")
                p.add_argument("--profile-only", action="store_true",
                               help="Output only a valid profile JSON for technique-save")
            if name == "annotate":
                p.add_argument("--model", required=True, help="Explicit external VLM model ID")
                p.add_argument("--endpoint", help="HTTPS JSON model endpoint")
                p.add_argument("--allow-external-upload", action="store_true",
                               help="Explicit permission in addition to source consent")
            if name == "propose":
                p.add_argument("--mode", default="palette_repaint",
                               choices=("palette_repaint", "material_study",
                                        "structure_study", "free_adaptation"))
                p.add_argument("--candidate-scene", help="Explicit alternative v4 plan for structural studies")
            if name == "approve":
                p.add_argument("--proposal", required=True)
                p.add_argument("--confirm", action="store_true")
            if name == "compare":
                p.add_argument("--kra", required=True)
                p.add_argument("--png", required=True)
                p.add_argument("--reopened", help="A separate freshly reopened native Krita PNG")
                p.add_argument("--native-plan-sha256")
        else:
            p.add_argument("--library", required=True)
            if name == "technique-save":
                p.add_argument("--profile", required=True)
            if name in ("technique-plan", "technique-approve"):
                p.add_argument("--scene", required=True)
                p.add_argument("--id", required=True)
                p.add_argument("--version", type=int, required=True)
                if name == "technique-plan":
                    p.add_argument("--subject", required=True)
                    p.add_argument("--intent", required=True)
                    p.add_argument("--build")
                else:
                    p.add_argument("--proposal", required=True)
                    p.add_argument("--confirm", action="store_true")
        if name not in ("technique-list", "technique-save"):
            p.add_argument("--output", help="Write once, refuse overwrite (otherwise print JSON)")


def execute(args):
    action = args.reference_action
    if action == "analyze":
        return _output(analyze_references(args.root, _load(args.manifest)), args.output)
    if action == "annotate":
        from .reference_vision_v10 import annotate_references
        from .model_provider import ChatJSONProvider
        if not args.allow_external_upload:
            raise ValueError("--allow-external-upload is required for model interpretation")
        return _output(annotate_references(
            args.root, _load(args.manifest),
            ChatJSONProvider(args.model, endpoint=args.endpoint),
            allow_external_upload=True,
        ), args.output)
    if action == "technique-extract":
        from .technique_extraction_v10 import extract_technique_hypothesis
        hypothesis = extract_technique_hypothesis(
            args.root, _load(args.manifest), source_id=args.source_id,
            region_id=args.region_id, profile_id=args.id,
            version=args.version, material=args.material, phase=args.phase,
        )
        return _output(hypothesis["profile"] if args.profile_only else hypothesis,
                       args.output)
    if action == "propose":
        return _output(propose_reference_repaint(
            _load(args.scene), _load(args.analysis), _load(args.bindings),
            mode=args.mode,
            candidate_scene=_load(args.candidate_scene) if args.candidate_scene else None,
        ), args.output)
    if action == "approve":
        return _output(approve_reference_repaint(
            _load(args.scene), _load(args.manifest), args.root, _load(args.proposal),
            confirm=args.confirm,
        ), args.output)
    if action == "compare":
        return _output(compare_native_repaint(
            _load(args.scene), _load(args.analysis), _load(args.bindings),
            args.kra, args.png, args.reopened,
            compiled_sha256=args.native_plan_sha256,
        ), args.output)
    if action == "technique-save":
        return save_technique(args.library, _load(args.profile))
    if action == "technique-list":
        return list_techniques(args.library)
    technique = load_technique(args.library, args.id, args.version)
    if action == "technique-plan":
        return _output(propose_technique_application(
            _load(args.scene), technique, args.subject, args.intent,
            build=args.build,
        ), args.output)
    if action == "technique-approve":
        return _output(approve_technique_application(
            _load(args.scene), technique, _load(args.proposal), confirm=args.confirm,
        ), args.output)
    raise ValueError("Unknown reference CLI operation")
