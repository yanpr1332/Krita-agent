"""Local, inspectable creative project manifest with artifact hashes, no secrets."""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

KINDS={"scene_plan","layer_graph","reference","preview","kra",
       "job_ledger","revision_plan","brush_evidence","report"}


def _hash(path):
    digest=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(262144),b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest(project_dir):
    return Path(project_dir).expanduser().resolve()/"krita-agent-project.json"


def _write(path,object):
    tmp=path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    try:
        with tmp.open("w",encoding="utf-8") as f:
            json.dump(object,f,indent=2,ensure_ascii=False,allow_nan=False)
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        tmp.unlink(missing_ok=True)


def init(project_dir,title):
    target=_manifest(project_dir)
    if target.exists():
        raise FileExistsError("Project already exists")
    if not isinstance(title,str) or not 1<=len(title)<=120:
        raise ValueError("Project title is invalid")
    target.parent.mkdir(parents=True,exist_ok=True)
    record={"schema":"krita-agent-project/1","id":uuid.uuid4().hex,
            "title":title,"created_at":datetime.now(timezone.utc).isoformat(),
            "artifacts":[],"status":"source_initialized",
            "note":"Only local paths and SHA256, never IPC credentials"}
    with target.open("x",encoding="utf-8") as f:
        json.dump(record,f,indent=2,ensure_ascii=False)
    return {"path":str(target),"id":record["id"]}


def show(project_dir):
    record=json.loads(_manifest(project_dir).read_text(encoding="utf-8"))
    if record.get("schema")!="krita-agent-project/1":
        raise ValueError("Wrong project schema")
    return record


def add(project_dir,filename,kind):
    if kind not in KINDS:
        raise ValueError("Unknown project artifact kind")
    file=Path(filename).expanduser().resolve()
    if not file.is_file():
        raise FileNotFoundError(file)
    if file.stat().st_size>2*1024*1024*1024:
        raise ValueError("Artifact exceeds 2 GiB")
    record=show(project_dir)
    relative=file.relative_to(Path(project_dir).resolve()) if Path(project_dir).resolve() in file.parents else str(file)
    item={"kind":kind,"path":str(relative),"sha256":_hash(file),
          "bytes":file.stat().st_size,"added_at":datetime.now(timezone.utc).isoformat()}
    if any(x["sha256"]==item["sha256"] and x["kind"]==kind for x in record["artifacts"]):
        raise ValueError("Same artifact was already recorded")
    record["artifacts"].append(item)
    _write(_manifest(project_dir),record)
    return item


def audit(project_dir):
    project=show(project_dir)
    root=Path(project_dir).resolve()
    status=[]
    for artifact in project["artifacts"]:
        path=Path(artifact["path"])
        if not path.is_absolute():
            path=root/path
        path=path.resolve()
        status.append({"kind":artifact["kind"],"path":str(path),
                       "valid":path.is_file() and _hash(path)==artifact["sha256"]})
    return {"project":project["id"],"artifacts":status,
            "all_valid":all(x["valid"] for x in status)}
