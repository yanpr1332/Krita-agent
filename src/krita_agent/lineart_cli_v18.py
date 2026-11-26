"""Offline-only Round 18 lineart CLI; never invokes Krita or a network client."""
import json
from pathlib import Path

from .protocol import TaskError
from .lineart_library_v18 import (
    analyze_library, retrieve, discover_article_images,
)
from .lineart_guides_v18 import trace_authorized, propose_scene_guides

MAX_JSON_BYTES=256*1024
MAX_HTML_BYTES=2*1024*1024


def _read(path,limit):
    source=Path(path).expanduser()
    if source.is_symlink() or not source.is_file() or source.stat().st_size>limit:
        raise TaskError("Local input missing, linked or exceeds budget")
    try:
        return source.read_text(encoding="utf-8")
    except (OSError,UnicodeError) as exc:
        raise TaskError("Unreadable local text input") from exc


def _json(path):
    try:
        return json.loads(_read(path,MAX_JSON_BYTES))
    except ValueError as exc:
        raise TaskError("Invalid offline JSON manifest") from exc


def _write_new(value,path):
    if path is None:
        return value
    target=Path(path).expanduser()
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with target.open("x",encoding="utf-8") as f:
            json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
            f.write("\n")
    except FileExistsError as exc:
        raise TaskError("Output exists; immutable lineart report will not overwrite") from exc
    return {
        "written":str(target),"exclusive_create":True,
        "native_effects":"none","network_requests":0,
    }


def register(commands):
    parser=commands.add_parser("lineart",help="Offline permitted lineart and article-image library (R18)")
    actions=parser.add_subparsers(dest="lineart_action",required=True)
    article=actions.add_parser("article-images",help="Discover image URLs from a saved HTML (NO downloads)")
    article.add_argument("--html",required=True)
    article.add_argument("--output")
    analyze=actions.add_parser("analyze",help="Analyze rights-approved images from an explicit local root")
    analyze.add_argument("--root",required=True)
    analyze.add_argument("--manifest",required=True)
    analyze.add_argument("--output")
    search=actions.add_parser("search",help="Filter local index metadata by tags and permissions")
    search.add_argument("--index",required=True)
    search.add_argument("--tag",action="append",required=True)
    search.add_argument("--purpose",default="local",
                        choices=("local","external_upload","training","publish"))
    search.add_argument("--limit",type=int,default=5)
    search.add_argument("--output")
    trace=actions.add_parser("trace",help="Local permitted thin-line centerline guide hypothesis")
    trace.add_argument("--root",required=True)
    trace.add_argument("--manifest",required=True)
    trace.add_argument("--source-id",required=True)
    trace.add_argument("--threshold",type=int,default=175)
    trace.add_argument("--max-paths",type=int,default=12)
    trace.add_argument("--output")
    bind=actions.add_parser("bind",help="Propose reviewed v4 sketch guides (NO painting)")
    bind.add_argument("--scene",required=True)
    bind.add_argument("--guides",required=True)
    bind.add_argument("--subject-id",required=True)
    bind.add_argument("--confirm-proposal",action="store_true")
    bind.add_argument("--output")


def execute(args):
    if args.lineart_action=="article-images":
        result=discover_article_images(_read(args.html,MAX_HTML_BYTES))
    elif args.lineart_action=="analyze":
        result=analyze_library(args.root,_json(args.manifest))
    elif args.lineart_action=="search":
        result={
            "schema":"krita-agent-lineart-search/1",
            "results":retrieve(_json(args.index),args.tag,args.purpose,args.limit),
            "purpose":args.purpose,"model_requests":0,
            "network_requests":0,"native_effects":"none",
        }
    elif args.lineart_action=="trace":
        result=trace_authorized(args.root,_json(args.manifest),
                                args.source_id,args.threshold,args.max_paths)
    elif args.lineart_action=="bind":
        result=propose_scene_guides(_json(args.scene),_json(args.guides),
                                    args.subject_id,confirm=args.confirm_proposal)
    else:
        raise TaskError("Unknown offline lineart action")
    return _write_new(result,args.output)
