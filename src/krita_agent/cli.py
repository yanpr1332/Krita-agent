"""Krita Agent command-line interface. Never silently launches Krita."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .client import BridgeError, Client
from .geometry import demo_task
from .protocol import TERMINAL_STATES, TaskError, compile_task, points
from .session import DEFAULT_PORT, launch, load_session
from . import upstream as upstream_api


def inspect(path, timeout=10):
    """Backward-compatible, read-only Krita executable inspection."""
    executable = Path(path).expanduser().resolve()
    result = {"path": str(executable), "exists": executable.is_file(),
              "version": None, "error": None, "runtime_capabilities": "not probed"}
    if not result["exists"]:
        result["error"] = "Executable does not exist or is not a file"
        return result
    try:
        completed = subprocess.run([str(executable), "--version"], capture_output=True,
                                   text=True, timeout=timeout, check=False,
                                   encoding="utf-8", errors="replace")
        output = (completed.stdout or completed.stderr).strip()
        if completed.returncode == 0 and output:
            result["version"] = output
        else:
            result["error"] = "Version command failed (exit {}): {}".format(completed.returncode, output)
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc) or type(exc).__name__
    return result


def _connection(parser):
    parser.add_argument("--session", help="Session JSON created by launch")
    parser.add_argument("--token", help="Bridge token; prefer KRITA_AGENT_TOKEN or --session")
    parser.add_argument("--port", type=int, help="Bridge port")


def _client(args):
    saved = {}
    if getattr(args, "session", None) or not getattr(args, "token", None):
        try:
            saved = load_session(getattr(args, "session", None))
        except (OSError, ValueError, json.JSONDecodeError):
            saved = {}
    token = getattr(args, "token", None) or os.getenv("KRITA_AGENT_TOKEN") or saved.get("token")
    port = getattr(args, "port", None) or int(os.getenv("KRITA_AGENT_PORT", saved.get("port", DEFAULT_PORT)))
    return Client(token, port)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _show(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def _call(args, name, **params):
    return _client(args).request(name, **params)


def parser_build():
    parser = argparse.ArgumentParser(prog="krita-agent", description="Native Krita painting automation")
    commands = parser.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="Read-only executable version probe")
    doctor.add_argument("--krita", help="Path to one Krita executable")
    doctor.add_argument("--stable", help="Stable Krita exe")
    doctor.add_argument("--next", help="Next Krita exe")

    start = commands.add_parser("launch", help="Launch an explicit Krita executable with local Bridge credentials")
    start.add_argument("--krita", required=True)
    start.add_argument("--port", type=int, default=DEFAULT_PORT)
    start.add_argument("--output-dir")
    start.add_argument("--session")

    for command in ("connect", "status", "capabilities"):
        _connection(commands.add_parser(command))

    canvas = commands.add_parser("canvas")
    canvas_actions = canvas.add_subparsers(dest="action", required=True)
    create = canvas_actions.add_parser("create")
    _connection(create)
    create.add_argument("--width", type=int, required=True)
    create.add_argument("--height", type=int, required=True)
    create.add_argument("--name", default="Krita Agent")

    layer = commands.add_parser("layer")
    layer_actions = layer.add_subparsers(dest="action", required=True)
    for name in ("add", "select", "list"):
        p = layer_actions.add_parser(name)
        _connection(p)
        if name != "list":
            p.add_argument("--name", required=True)

    brush = commands.add_parser("brush")
    b = brush.add_subparsers(dest="action", required=True).add_parser("set")
    _connection(b)
    b.add_argument("--preset")
    b.add_argument("--size", type=float)
    b.add_argument("--opacity", type=float)
    b.add_argument("--color")
    b.add_argument("--pressure-enabled", choices=("true", "false"))

    draw = commands.add_parser("draw")
    draw_actions = draw.add_subparsers(dest="action", required=True)
    demo = draw_actions.add_parser("demo")
    _connection(demo)
    demo.add_argument("--wait", action="store_true")
    stroke = draw_actions.add_parser("stroke")
    _connection(stroke)
    stroke.add_argument("--file", required=True, help="JSON list of points or object with points")
    stroke.add_argument("--mode", choices=("auto", "continuous", "segmented"), default="auto")
    line = draw_actions.add_parser("line")
    _connection(line)
    line.add_argument("--x1", type=float, required=True)
    line.add_argument("--y1", type=float, required=True)
    line.add_argument("--x2", type=float, required=True)
    line.add_argument("--y2", type=float, required=True)
    line.add_argument("--pressure1", type=float, default=1)
    line.add_argument("--pressure2", type=float, default=1)

    for command in ("save", "export"):
        p = commands.add_parser(command)
        _connection(p)
        p.add_argument("path")
        p.add_argument("--overwrite", action="store_true")

    job = commands.add_parser("job")
    job_actions = job.add_subparsers(dest="action", required=True)
    run = job_actions.add_parser("run")
    _connection(run)
    run.add_argument("--file", required=True)
    run.add_argument("--wait", action="store_true")
    for action in ("status", "pause", "resume", "cancel"):
        p = job_actions.add_parser(action)
        _connection(p)
        p.add_argument("id")
    _connection(job_actions.add_parser("list"))

    up = commands.add_parser("upstream", help="Read-only upstream inspection; writes only with explicit action")
    up.add_argument("--repo", default=r"D:\computer\Krita\Krita-upstream")
    up.add_argument("--baseline-file", default=".cache/upstream-baseline.json")
    up.add_argument("--from-sha", dest="base")
    up.add_argument("--to-sha", default="HEAD")
    up.add_argument("--fetch", action="store_true")
    up.add_argument("--update-baseline", action="store_true")
    up.add_argument("--write-report")
    up.add_argument("action", nargs="?", choices=("snapshot", "init", "check", "diff"),
                    default="snapshot")
    return parser


def _wait_for_job(client, job_id):
    while True:
        result = client.request("job.status", id=job_id)
        if result.get("state") in TERMINAL_STATES:
            return result
        time.sleep(0.3)


def main(argv=None):
    try:
        args = parser_build().parse_args(argv)
        if args.command == "doctor":
            options = [(key, getattr(args, key)) for key in ("krita", "stable", "next")
                       if getattr(args, key)]
            if not options:
                options = [("stable", r"D:\computer\Krita\Krita (x64)\bin\krita.exe"),
                           ("next", r"D:\computer\Krita\Krita_Next\bin\krita.exe")]
            result = {key: inspect(value) for key, value in options}
            _show(result if len(result) > 1 or not args.krita else result["krita"])
            return 1 if any(entry["error"] for entry in result.values()) else 0
        if args.command == "launch":
            _show(launch(args.krita, args.port, args.output_dir, args.session))
            return 0
        if args.command == "upstream":
            if args.action == "snapshot":
                result = upstream_api.snapshot(args.repo)
            elif args.action == "init":
                result = upstream_api.initialize(args.repo, args.baseline_file)
            elif args.action == "check":
                result = upstream_api.check(args.repo, args.baseline_file, args.fetch,
                                            args.update_baseline)
            else:
                if not args.base:
                    raise ValueError("upstream diff requires --from-sha")
                result = upstream_api.compare(args.repo, args.base, args.to_sha)
            if args.write_report:
                result["report_file"] = upstream_api.write_report(result, args.write_report)
            _show(result)
            return 0
        if args.command in ("connect", "status", "capabilities"):
            _show(_call(args, "capabilities" if args.command == "capabilities" else "status"))
        elif args.command == "canvas":
            _show(_call(args, "canvas.create", width=args.width, height=args.height, name=args.name))
        elif args.command == "layer":
            cmd = {"add": "layer.create", "select": "layer.select", "list": "layer.list"}[args.action]
            _show(_call(args, cmd, **({"name": args.name} if args.action != "list" else {})))
        elif args.command == "brush":
            config = {name: getattr(args, name) for name in ("preset", "size", "opacity", "color")
                      if getattr(args, name) is not None}
            if args.pressure_enabled is not None:
                config["pressure_enabled"] = args.pressure_enabled == "true"
            _show(_call(args, "brush.configure", **config))
        elif args.command == "draw":
            if args.action == "line":
                _show(_call(args, "draw.line", x1=args.x1, y1=args.y1, x2=args.x2, y2=args.y2,
                            pressure1=args.pressure1, pressure2=args.pressure2))
            elif args.action == "stroke":
                data = _read_json(args.file)
                sample = data["points"] if isinstance(data, dict) else data
                _show(_call(args, "draw.stroke", points=points(sample), mode=args.mode))
            else:
                client = _client(args)
                result = client.submit(compile_task(demo_task()))
                _show(_wait_for_job(client, result["id"]) if args.wait else result)
        elif args.command in ("save", "export"):
            _show(_call(args, "document.save" if args.command == "save" else "document.export",
                        path=args.path, overwrite=args.overwrite))
        elif args.command == "job":
            if args.action == "run":
                client = _client(args)
                result = client.submit(compile_task(_read_json(args.file)))
                _show(_wait_for_job(client, result["id"]) if args.wait else result)
            elif args.action == "list":
                _show(_call(args, "job.list"))
            else:
                _show(_call(args, "job." + args.action, id=args.id))
        return 0
    except (BridgeError, TaskError, OSError, ValueError, KeyError,
            json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        _show({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
