"""Round 4 CLI adapter. Adding commands here avoids further monolith growth."""
import json
from pathlib import Path
from . import document_graph, large_canvas, layered_revision
from . import scheduler, brush_profiles, feedback_v2, scene_v2, projects
from . import performance, pyramid


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(value,path):
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf-8") as f:
        json.dump(value,f,indent=2,ensure_ascii=False)
    return str(target)


def register(commands,connection):
    graph=commands.add_parser("graph",help="Capture and compare editable document graphs")
    acts=graph.add_subparsers(dest="action",required=True)
    capture=acts.add_parser("capture")
    connection(capture)
    capture.add_argument("--output",required=True)
    for command in ("diff","rebind"):
        p=acts.add_parser(command)
        p.add_argument("--before",required=True)
        p.add_argument("--after",required=True)

    overlay=commands.add_parser("overlay",help="Conservative layered goal-image revision")
    oa=overlay.add_subparsers(dest="action",required=True)
    plan=oa.add_parser("plan")
    for name in ("before","target","graph","output"):
        plan.add_argument("--"+name,required=True)
    plan.add_argument("--tile-size",type=int,default=512)
    apply=oa.add_parser("apply")
    connection(apply)
    apply.add_argument("--plan",required=True)
    apply.add_argument("--confirm",action="store_true")
    apply.add_argument("--no-wait",action="store_true")

    longjob=commands.add_parser("longjob",help="Serial checkpointed batches (no auto replay)")
    la=longjob.add_subparsers(dest="action",required=True)
    for action in ("plan","run"):
        p=la.add_parser(action)
        if action=="run":
            connection(p)
        p.add_argument("--file",required=True)
        p.add_argument("--batch-size",type=int,default=120)
        p.add_argument("--ledger-dir",default=".cache/long-jobs")
    li=la.add_parser("inspect")
    li.add_argument("--file",required=True)

    brush=commands.add_parser("brushcal",help="Evidence-based native brush catalogue")
    ba=brush.add_subparsers(dest="action",required=True)
    generate=ba.add_parser("generate")
    generate.add_argument("--preset",required=True)
    generate.add_argument("--size",type=float,default=24)
    generate.add_argument("--output",required=True)
    record=ba.add_parser("record")
    record.add_argument("--data",required=True)
    record.add_argument("--evidence",required=True)
    record.add_argument("--directory",default=".cache/brush-profiles")
    for action in ("list","choose"):
        p=ba.add_parser(action)
        p.add_argument("--directory",default=".cache/brush-profiles")
        p.add_argument("--build")
        p.add_argument("--category")
        p.add_argument("--min-confidence",type=float,default=.8)

    pyr=commands.add_parser("pyramid",help="Build offline tile pyramid from a source image")
    pa=pyr.add_subparsers(dest="action",required=True)
    pb=pa.add_parser("build")
    pb.add_argument("--image",required=True)
    pb.add_argument("--output-dir",required=True)
    pb.add_argument("--tile-size",type=int,default=512)
    pi=pa.add_parser("inspect")
    pi.add_argument("--manifest",required=True)

    scene=commands.add_parser("scene-v2",help="Human-reviewable structured painting")
    sa=scene.add_subparsers(dest="action",required=True)
    for action in ("compile","submit"):
        p=sa.add_parser(action)
        p.add_argument("--file",required=True)
        p.add_argument("--output")
        p.add_argument("--profiles-directory")
        p.add_argument("--build")
        if action=="submit":
            connection(p)
            p.add_argument("--ledger-dir",default=".cache/long-jobs")
            p.add_argument("--batch-size",type=int,default=120)

    review=commands.add_parser("feedback-v2",help="Bounded human-reviewed revisions")
    rv=review.add_subparsers(dest="action",required=True).add_parser("review")
    for name in ("current","goal","graph","output"):
        rv.add_argument("--"+name,required=True)
    rv.add_argument("--round",type=int,default=0)
    rv.add_argument("--max-rounds",type=int,default=3)

    prj=commands.add_parser("project",help="Durable local art-project manifest")
    ps=prj.add_subparsers(dest="action",required=True)
    for action in ("init","show","audit","add"):
        p=ps.add_parser(action)
        p.add_argument("--directory",required=True)
        if action=="init":
            p.add_argument("--title",required=True)
        if action=="add":
            p.add_argument("--file",required=True)
            p.add_argument("--kind",required=True,choices=sorted(projects.KINDS))

    performance_cmd=commands.add_parser("performance")
    pa=performance_cmd.add_subparsers(dest="action",required=True)
    for action in ("ledger","job"):
        p=pa.add_parser(action)
        if action=="ledger":
            p.add_argument("--file",required=True)
        else:
            connection(p)
            p.add_argument("--id",required=True)


def execute(args,get_client):
    cmd=args.command
    if cmd=="graph":
        if args.action=="capture":
            return {"saved":document_graph.save(get_client(args).request("document.graph"),args.output)}
        before,after=_read(args.before),_read(args.after)
        return (document_graph.changed_nodes(before,after) if args.action=="diff"
                else document_graph.rebind(before,after))
    if cmd=="overlay":
        return (layered_revision.create_plan(args.before,args.target,args.graph,args.output,args.tile_size)
                if args.action=="plan"
                else layered_revision.apply(get_client(args),layered_revision.load(args.plan),
                                            confirm=args.confirm,wait=not args.no_wait))
    if cmd=="longjob":
        if args.action=="inspect":
            return scheduler.inspect_ledger(args.file)
        batches=scheduler.split_workflow(_read(args.file),args.batch_size)
        if args.action=="plan":
            return {"batches":len(batches),"total_steps":sum(len(b)-1 for b in batches),
                    "max_batch_steps":max(map(len,batches)),
                    "run_required":"Explicit longjob run"}
        return scheduler.run(get_client(args),_read(args.file),args.ledger_dir,args.batch_size)
    if cmd=="brushcal":
        if args.action=="generate":
            return {"saved":_dump(brush_profiles.calibration_task(args.preset,args.size),args.output)}
        if args.action=="record":
            return brush_profiles.record_profile(args.directory,_read(args.data),args.evidence)
        if args.action=="list":
            return brush_profiles.find_profiles(args.directory,args.build,args.category,args.min_confidence)
        if not (args.build and args.category):
            raise ValueError("Brush choice requires --build and --category")
        return brush_profiles.choose(args.directory,args.build,args.category,args.min_confidence)
    if cmd=="pyramid":
        return (pyramid.build(args.image,args.output_dir,args.tile_size)
                if args.action=="build" else pyramid.inspect(args.manifest))
    if cmd=="scene-v2":
        plan=scene_v2.compile_plan(_read(args.file),args.profiles_directory,args.build)
        if args.output:
            _dump(plan,args.output)
        if args.action=="compile":
            return {"schema":plan["schema"],"steps":len(plan["steps"]),
                    "sha256":plan["sha256"],"output":args.output,"submitted":False}
        return scheduler.run(get_client(args),{"steps":plan["steps"]},args.ledger_dir,args.batch_size)
    if cmd=="feedback-v2":
        review=feedback_v2.review_iteration(args.current,args.goal,_read(args.graph),
                                           args.round,args.max_rounds)
        return {"saved":feedback_v2.write_review(review,args.output),
                "next":review["next"],"evaluation":review["evaluation"]}
    if cmd=="project":
        if args.action=="init":
            return projects.init(args.directory,args.title)
        if args.action=="show":
            return projects.show(args.directory)
        if args.action=="audit":
            return projects.audit(args.directory)
        return projects.add(args.directory,args.file,args.kind)
    if cmd=="performance":
        return (performance.summarize_ledger(args.file) if args.action=="ledger"
                else get_client(args).request("job.metrics",id=args.id))
    raise ValueError("Unknown Round 4 command")
