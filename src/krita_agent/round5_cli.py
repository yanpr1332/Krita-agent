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
    return ChatJSONProvider(model, endpoint=getattr(args, "endpoint", None))


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
        "status", "dashboard", "plan", "approve", "paint", "export",
        "record", "critique", "revision-plan", "revision-approve",
        "revise", "deliver",
    ):
        p = actions.add_parser(name)
        p.add_argument("--directory", required=True)
        if name in ("paint", "export", "revise"):
            connection(p)
        if name in ("approve", "revision-approve", "revise"):
            p.add_argument("--confirm", action="store_true")
        if name in ("plan", "critique", "revision-plan"):
            p.add_argument("--model", help="Opt-in OpenAI-compatible JSON model ID")
            p.add_argument("--endpoint", help="Optional HTTPS chat-completions endpoint")
        if name == "dashboard":
            p.add_argument("--output", help="HTML output inside the run directory")
            p.add_argument("--replace", action="store_true")
        if name == "plan":
            p.add_argument("--candidate", help="Explicit user-authored ScenePlan v3 JSON")
            p.add_argument("--reference", help="Actual reference image, optional")
            p.add_argument("--profiles-directory")
            p.add_argument("--build")
        if name == "paint":
            p.add_argument("--ledger-dir")
            p.add_argument("--batch-size", type=int, default=120)
        if name == "record":
            p.add_argument("--kra", required=True)
            p.add_argument("--png", required=True)
        if name == "critique":
            p.add_argument("--reference", help="Actual benchmark/reference image")
            p.add_argument("--max-rounds", type=int, default=3)
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
    if args.action == "plan":
        candidate = _json(args.candidate) if args.candidate else None
        return flow.plan(
            candidate=candidate,
            provider=_provider(args) if not args.candidate else None,
            reference=args.reference,
            profile_directory=args.profiles_directory,
            build=args.build,
        )
    if args.action == "approve":
        return flow.approve_plan(confirm=args.confirm)
    if args.action == "paint":
        return flow.paint(get_client(args), args.ledger_dir, args.batch_size)
    if args.action == "export":
        return flow.export_native(get_client(args))
    if args.action == "record":
        return flow.record_artwork(args.kra, args.png)
    if args.action == "critique":
        return flow.critique(
            _provider(args), reference=args.reference, max_rounds=args.max_rounds
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
