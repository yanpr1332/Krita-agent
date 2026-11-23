"""Round 5 creative-workflow CLI: explicit, review-first stages."""
import json
from pathlib import Path

from .creative_workflow import CreativeWorkflow
from .creative_dashboard import render as render_dashboard
from .model_provider import ChatJSONProvider


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _provider(args):
    model = getattr(args, "model", None)
    if not model:
        raise ValueError("A model ID is required unless an explicit candidate JSON file is supplied")
    return ChatJSONProvider(model, endpoint=getattr(args, "endpoint", None),
                           timeout=getattr(args, "timeout", 75))


def register(commands, connection):
    creative = commands.add_parser(
        "creative", help="Multi-stage native Krita creative workflow (Round 5)"
    )
    actions = creative.add_subparsers(dest="action", required=True)
    initial = actions.add_parser("init", help="Initialize a new immutable creative run")
    initial.add_argument("--directory", required=True)
    initial.add_argument("--brief-file", required=True,
                         help="A JSON creative brief or a plain-text prompt")
    for name in (
        "status", "dashboard", "diagnose", "plan", "approve", "paint", "paint-stage", "export",
        "record", "verify-reopen", "critique", "critique-v11", "revision-plan", "revision-approve",
        "revise", "deliver",
    ):
        p = actions.add_parser(name)
        p.add_argument("--directory", required=True)
        if name in ("paint", "paint-stage", "export", "revise", "record", "verify-reopen"):
            connection(p)
        if name in ("approve", "paint-stage", "revision-approve", "revise"):
            p.add_argument("--confirm", action="store_true")
        if name in ("plan", "critique", "critique-v11", "revision-plan"):
            p.add_argument("--model", help="Opt-in OpenAI-compatible JSON model ID")
            p.add_argument("--endpoint", help="Optional HTTPS chat-completions endpoint")
        if name == "dashboard":
            p.add_argument("--output", help="HTML output inside the run directory")
            p.add_argument("--replace", action="store_true")
        if name == "plan":
            p.add_argument("--candidate", help="User-authored ScenePlan v3 or v4 JSON")
            p.add_argument("--generalist", action="store_true",
                           help="Request a generalist StagePlan v4 from a model")
            p.add_argument("--reference", help="Actual reference image, optional")
            p.add_argument("--profiles-directory")
            p.add_argument("--build")
        if name in ("paint", "paint-stage"):
            p.add_argument("--ledger-dir")
            p.add_argument("--batch-size", type=int, default=120)
        if name == "record":
            p.add_argument("--kra", required=True)
            p.add_argument("--png", required=True)
            p.add_argument("--new-version", action="store_true",
                           help="Archive repaired files as a NEW version after a failed integrity gate")
            p.add_argument("--confirm", action="store_true",
                           help="Required with --new-version")
            p.add_argument("--defer-reopen", action="store_true",
                           help="Explicitly defer native reopening; artwork remains blocked")
        if name == "critique":
            p.add_argument("--reference", help="Actual benchmark/reference image")
            p.add_argument("--max-rounds", type=int, default=3)
        if name == "critique-v11":
            p.add_argument("--confirm-external-review", action="store_true",
                           help="Confirm this operation may send selected evidence to the configured external provider")
            p.add_argument("--upload-artwork", action="store_true",
                           help="Explicitly permit upload of the final artwork PNG")
            p.add_argument("--reference", help="Optional reference image")
            p.add_argument("--upload-reference", action="store_true")
            p.add_argument("--confirm-reference-rights", action="store_true",
                           help="Confirm the reference may legally be sent to this provider")
            p.add_argument("--stage-preview", action="append", default=[], metavar="LABEL=FILE")
            p.add_argument("--upload-stages", action="store_true")
            p.add_argument("--upload-rois", action="store_true")
            p.add_argument("--layer-graph", help="Optional JSON layer graph metadata")
            p.add_argument("--layer-contributions", help="Optional JSON layer contribution metadata")
            p.add_argument("--upload-layer-metadata", action="store_true")
            p.add_argument("--constraints", help="Optional JSON target constraints")
            p.add_argument("--max-rounds", type=int)
            p.add_argument("--max-revisions", type=int)
            p.add_argument("--max-calls", type=int)
            p.add_argument("--max-images", type=int)
            p.add_argument("--max-output-tokens", type=int)
            p.add_argument("--price-input-usd-per-million", type=float)
            p.add_argument("--price-output-usd-per-million", type=float)
            p.add_argument("--max-total-cost-usd", type=float)
            p.add_argument("--timeout", type=float, default=75)
        if name == "revision-plan":
            p.add_argument("--object-id", required=True)
            p.add_argument("--candidate", help="Explicit candidate native stroke JSON")
            p.add_argument("--issue-id", help="Required with --candidate")
        if name == "revise":
            p.add_argument("--ledger-dir")
            p.add_argument("--graph-sha256", help="Optional approved live graph fingerprint")


def execute(args, get_client):
    if args.action == "init":
        path = Path(args.brief_file)
        raw = path.read_text(encoding="utf-8")
        try:
            brief = json.loads(raw)
        except json.JSONDecodeError:
            brief = raw
        workflow = CreativeWorkflow.create(args.directory, brief)
        return {"status": "initialized", "path": str(workflow.manifest)}
    flow = CreativeWorkflow(args.directory)
    if args.action == "status":
        return flow.read()
    if args.action == "dashboard":
        return render_dashboard(flow, args.output, replace=args.replace)
    if args.action == "diagnose":
        return flow.diagnose_materials()
    if args.action == "plan":
        candidate = _json(args.candidate) if args.candidate else None
        return flow.plan(
            candidate=candidate,
            provider=_provider(args) if not args.candidate else None,
            reference=args.reference,
            profile_directory=args.profiles_directory,
            build=args.build,
            generalist=args.generalist,
        )
    if args.action == "approve":
        return flow.approve_plan(confirm=args.confirm)
    if args.action == "paint":
        return flow.paint(get_client(args), args.ledger_dir, args.batch_size)
    if args.action == "paint-stage":
        return flow.paint_stage(get_client(args), confirm=args.confirm,
                                ledger_directory=args.ledger_dir,
                                batch_steps=args.batch_size)
    if args.action == "export":
        return flow.export_native(get_client(args))
    if args.action == "record":
        if args.new_version and not args.confirm:
            raise ValueError("--new-version requires --confirm")
        result = flow.record_artwork(args.kra, args.png,
                                     confirm_new_version=args.new_version and args.confirm)
        if result["status"] == "awaiting_reopen" and not args.defer_reopen:
            return flow.verify_reopen(get_client(args))
        return result
    if args.action == "verify-reopen":
        return flow.verify_reopen(get_client(args))
    if args.action == "critique":
        return flow.critique(
            _provider(args), reference=args.reference, max_rounds=args.max_rounds
        )
    if args.action == "critique-v11":
        if not args.confirm_external_review or not args.upload_artwork:
            raise ValueError("Round 11 requires --confirm-external-review and --upload-artwork")
        if args.reference and (not args.upload_reference or not args.confirm_reference_rights):
            raise ValueError("Reference upload requires --upload-reference and --confirm-reference-rights")
        if not args.reference and (args.upload_reference or args.confirm_reference_rights):
            raise ValueError("Reference upload flags require --reference")
        if args.stage_preview and not args.upload_stages:
            raise ValueError("Explicit stage previews require --upload-stages")
        if (args.layer_graph or args.layer_contributions) and not args.upload_layer_metadata:
            raise ValueError("Layer metadata files require --upload-layer-metadata")
        stages = {}
        for item in args.stage_preview:
            if "=" not in item:
                raise ValueError("--stage-preview requires LABEL=FILE")
            name, filename = item.split("=", 1)
            if not name or not filename or name in stages:
                raise ValueError("Stage preview labels must be unique and non-empty")
            stages[name] = filename
        consent = {
            "confirmed": True, "artwork_upload": True,
            "reference_upload": args.upload_reference,
            "reference_rights_confirmed": args.confirm_reference_rights,
            "stage_upload": args.upload_stages, "roi_upload": args.upload_rois,
            "layer_metadata_upload": args.upload_layer_metadata,
        }
        return flow.critique_v11(
            _provider(args), consent=consent, reference=args.reference,
            stage_previews=stages or None,
            layer_graph=args.layer_graph, layer_contributions=args.layer_contributions,
            target_constraints=_json(args.constraints) if args.constraints else None,
            max_rounds=args.max_rounds, max_revisions=args.max_revisions,
            max_calls=args.max_calls, max_images=args.max_images,
            max_output_tokens=args.max_output_tokens,
            input_usd_per_million=args.price_input_usd_per_million,
            output_usd_per_million=args.price_output_usd_per_million,
            max_total_cost_usd=args.max_total_cost_usd,
        )
    if args.action == "revision-plan":
        candidate = _json(args.candidate) if args.candidate else None
        return flow.propose_revision(
            args.object_id,
            candidate=candidate,
            provider=_provider(args) if not args.candidate else None,
            issue_id=args.issue_id,
        )
    if args.action == "revision-approve":
        return flow.approve_revision(confirm=args.confirm)
    if args.action == "revise":
        return flow.apply_revision(
            get_client(args), confirm=args.confirm,
            ledger_directory=args.ledger_dir, graph_sha256=args.graph_sha256,
        )
    if args.action == "deliver":
        return flow.prepare_delivery()
    raise ValueError("Unsupported creative workflow action")
