"""Round 19 offline actual-PNG review triage; no paid model or Krita launch."""
from .art_diagnostics_v19 import triage, verify_triage
from .lineart_cli_v18 import _json, _write_new


def register(commands):
    parser=commands.add_parser("art-review",help="Image-grounded bounded revision queue (R19)")
    actions=parser.add_subparsers(dest="art_review_action",required=True)
    task=actions.add_parser("triage",help="Prioritize review issues using actual local PNG pixels")
    task.add_argument("--scene",required=True)
    task.add_argument("--png",required=True)
    task.add_argument("--review",required=True)
    task.add_argument("--max-tickets",type=int,default=6)
    task.add_argument("--max-area-fraction",type=float,default=.2)
    task.add_argument("--output")
    check=actions.add_parser("verify",help="Recheck source hashes and triage on unchanged PNG")
    check.add_argument("--report",required=True)
    check.add_argument("--scene",required=True)
    check.add_argument("--png",required=True)
    check.add_argument("--review",required=True)


def execute(args):
    scene=_json(args.scene)
    review=_json(args.review)
    if args.art_review_action=="triage":
        report=triage(scene,args.png,review,args.max_tickets,
                      args.max_area_fraction)
        return _write_new(report,args.output)
    if args.art_review_action=="verify":
        return verify_triage(_json(args.report),scene,args.png,review)
    raise ValueError("Unknown art-review action")
