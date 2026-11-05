"""Build-specific capability matrices with proof provenance; source-only is not verified."""
import json
import hashlib
from pathlib import Path
from .protocol_v2 import Capability


def assemble(probes, registry):
    if not isinstance(probes,dict) or not isinstance(registry,dict):
        raise ValueError("Probes/registry must be JSON objects")
    entries=registry.get("entries",[])
    if not isinstance(entries,list):
        raise ValueError("Bad evidence registry")
    approved={}
    for record in entries:
        if record.get("reviewer_confirmed") is not True or record.get("state") != "tested_working":
            continue
        evidence = Path(record.get("evidence_path", ""))
        try:
            if evidence.is_file() and evidence.stat().st_size <= 2000000 and hashlib.sha256(evidence.read_bytes()).hexdigest() == record.get("evidence_sha256"):
                approved[(record["build"], record["symbol"])] = record
        except OSError:
            continue
    result={}
    for build,report in probes.items():
        symbols=report.get("symbols",report)
        result[build]={}
        for name,present in symbols.items():
            if type(present) is not bool:
                continue
            rec=approved.get((build,name))
            level=("tested_working" if present and rec else
                   "present_in_build" if present else "not_supported")
            result[build][name]=Capability(name,build,level,bool(present and rec)).as_dict()
    return {"schema":"krita-agent-capabilities/2",
            "builds":result,"source_evidence_is_not_runtime_proof":True}


def save_matrix(matrix,path):
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf-8") as out:
        json.dump(matrix,out,indent=2,ensure_ascii=False)
    return str(target)
