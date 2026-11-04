"""Build a reviewable Krita user-plugin ZIP. Does not install or run Krita."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def build(output):
    repo=Path(__file__).resolve().parents[1]
    module=repo/"plugin"/"krita_agent_bridge"
    desktop=repo/"plugin"/"krita_agent_bridge.desktop"
    target=Path(output).expanduser().resolve()
    if target.exists():
        raise FileExistsError("Refusing to overwrite existing plugin bundle")
    if target.suffix.lower()!=".zip":
        raise ValueError("Bundle must be .zip")
    if not module.is_dir() or not desktop.is_file():
        raise FileNotFoundError("Plugin entry files missing")
    entries=[(desktop,"pykrita/krita_agent_bridge.desktop")]
    for path in sorted(module.rglob("*.py")):
        if path.is_symlink():
            raise ValueError("Plugin symlink not permitted in package")
        entries.append((path,"pykrita/krita_agent_bridge/"+
                         path.relative_to(module).as_posix()))
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
        for source,name in entries:
            archive.write(source,name)
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    return {"archive":str(target),"sha256":digest,"files":len(entries),
            "install_required":True,
            "note":"Inspect files and back up shared Krita user resources before deploying"}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.output),indent=2))
