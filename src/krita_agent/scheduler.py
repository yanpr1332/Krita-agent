"""Durable orchestration of many bounded Krita jobs.

This module does not increase Bridge wire limits. Each sub-job uses existing
authenticated IPC and existing one-job checkpoint semantics. A lost reply is
UNKNOWN, never an automatic re-submit; no duplicate brush strokes.
"""
import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from .protocol import TaskError
from .workflow import compile_workflow

MAX_TOTAL_STEPS=10000
MAX_WIRE_BYTES=750000


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def split_workflow(spec, batch_steps=120):
    if not isinstance(spec, dict) or not isinstance(spec.get("steps"), list):
        raise TaskError("Long workflow requires an explicit steps array")
    if type(batch_steps) is not int or not 1 <= batch_steps <= 380:
        raise TaskError("Batch size must be in [1,380]")
    raw=spec["steps"]
    if not 1 <= len(raw) <= MAX_TOTAL_STEPS:
        raise TaskError("Long workflow accepts 1..10000 steps")
    prepared=[]
    # Validate one at a time, keeping existing per-command policy identical.
    for step in raw:
        compiled=compile_workflow({"steps":[step]})[0]
        encoded=json.dumps(compiled,ensure_ascii=False,allow_nan=False).encode("utf-8")
        if len(encoded)>MAX_WIRE_BYTES-4096:
            raise TaskError("A single step exceeds IPC budget; split stroke intentionally")
        prepared.append(compiled)
    batches=[]
    cursor=[]
    for step in prepared:
        proposed=cursor+[step,{"command":"checkpoint.create","parameters":{}}]
        if cursor and (len(cursor)>=batch_steps or
                       len(json.dumps(proposed,ensure_ascii=False,allow_nan=False).encode("utf-8"))>MAX_WIRE_BYTES):
            batches.append(cursor+[{"command":"checkpoint.create","parameters":{}}])
            cursor=[]
        cursor.append(step)
    if cursor:
        batches.append(cursor+[{"command":"checkpoint.create","parameters":{}}])
    return batches


class Ledger:
    """Single-writer atomic ledger with explicit unknown state after exceptions."""
    def __init__(self, directory, identifier=None):
        self.root=Path(directory).expanduser().resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.id=identifier or uuid.uuid4().hex
        if not len(self.id)==32 or any(c not in "0123456789abcdef" for c in self.id):
            raise ValueError("Invalid ledger ID")
        self.path=self.root/("long-job-"+self.id+".json")

    def write(self, value):
        temp=self.path.with_name(self.path.name+"."+uuid.uuid4().hex+".tmp")
        try:
            with temp.open("w",encoding="utf-8") as f:
                json.dump(value,f,ensure_ascii=False,allow_nan=False,indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp,self.path)
        finally:
            temp.unlink(missing_ok=True)

    def read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))


def run(client, spec, ledger_dir, batch_steps=120, poll_interval=0.3,
        terminal_timeout=1800, on_progress=None):
    """Submit serial bounded batches. On failure return a forensic ledger.

    Use a new client session for each invocation. Replaying this function after
    a transport timeout is intentionally NOT an automatic resume mechanism.
    """
    batches=split_workflow(spec,batch_steps)
    ledger=Ledger(ledger_dir)
    record={"schema":"krita-agent-long-job/1","id":ledger.id,
            "state":"prepared","source_sha256":_digest(spec),
            "batch_count":len(batches),"next_batch":0,
            "completed":[],"current":None,
            "policy":"no auto replay of uncertain native effects"}
    ledger.write(record)
    for index, batch in enumerate(batches):
        # Persist intent BEFORE submission; if the server receives a request
        # and the response is lost, we must not retry it blindly.
        record["state"]="submitting"
        record["current"]={"index":index,"batch_sha256":_digest(batch),
                           "job_id":None,"state":"unknown"}
        ledger.write(record)
        try:
            result=client.submit(batch)
            record["current"]["job_id"]=result["id"]
            record["current"]["state"]="submitted"
            record["state"]="running"
            ledger.write(record)
            started=time.monotonic()
            while True:
                if time.monotonic()-started>terminal_timeout:
                    raise TimeoutError("Sub-job completion not confirmed")
                status=client.request("job.status",id=result["id"])
                record["current"]["done"]=status["done"]
                record["current"]["state"]=status["state"]
                ledger.write(record)
                if on_progress is not None:
                    on_progress({"batch":index+1,"total_batches":len(batches),"job":status})
                if status["state"]=="completed":
                    record["completed"].append({"index":index,"job_id":result["id"],
                                                "checkpoint":status.get("last_result")})
                    record["next_batch"]=index+1
                    record["current"]=None
                    record["state"]="ready_for_next_batch"
                    ledger.write(record)
                    break
                if status["state"] in ("failed","cancelled","interrupted"):
                    raise RuntimeError("Sub-job ended in "+status["state"]+"; inspect saved checkpoint")
                time.sleep(poll_interval)
        except Exception as exc:
            record["state"]="unknown_needs_review"
            record["error"]=str(exc)
            ledger.write(record)
            return {"state":record["state"],"ledger":str(ledger.path),
                    "completed_batches":len(record["completed"]),"error":str(exc)}
    record["state"]="completed"
    record["current"]=None
    ledger.write(record)
    return {"state":"completed","ledger":str(ledger.path),"batches":len(batches)}


def inspect_ledger(path):
    record=json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("schema")!="krita-agent-long-job/1":
        raise ValueError("Not a recognized long-job ledger")
    return record
