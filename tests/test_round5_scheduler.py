import hashlib
import json
from pathlib import Path
import uuid

import pytest

from krita_agent.scheduler import (
    Ledger, _digest, inspect_ledger, resume, run, split_workflow,
)
from krita_agent.protocol import TaskError


def task(n=450):
    return {"steps": [
        {"command": "layer.create", "parameters": {"name": "Frame-" + str(i)}}
        for i in range(n)
    ]}


def checkpoint(path):
    path.write_bytes(b"test KRA checkpoint")
    return {
        "id": uuid.uuid4().hex,
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "document_name": "Resume fixture",
        "width": 512,
        "height": 512,
    }


def test_very_long_steps_split_with_checkpoints():
    batches = split_workflow(task(), batch_steps=90)
    assert len(batches) > 4
    assert all(len(batch) <= 91 for batch in batches)
    assert all(batch[-1]["command"] == "checkpoint.create" for batch in batches)
    assert sum(len(batch) - 1 for batch in batches) == 450


def test_unsupported_and_overlength_rejected():
    with pytest.raises(TaskError):
        split_workflow({"steps": [{"command": "shell", "parameters": {}}]})
    with pytest.raises(TaskError):
        split_workflow(task(450), batch_steps=400)


def test_unknown_reply_does_not_retry(tmp_path):
    class LostReply:
        times = 0

        def submit(self, steps):
            self.times += 1
            raise TimeoutError("Lost confirmation after possible native effect")

    client = LostReply()
    result = run(client, task(6), tmp_path, batch_steps=3)
    assert client.times == 1
    assert result["state"] == "unknown_needs_review"
    saved = inspect_ledger(result["ledger"])
    assert saved["current"]["job_id"] is None
    assert saved["next_batch"] == 0


def ready_ledger(tmp_path, spec, batch_steps=2):
    batches = split_workflow(spec, batch_steps)
    identifier = uuid.uuid4().hex
    ledger = Ledger(tmp_path, identifier)
    first_checkpoint = checkpoint(tmp_path / "batch-0.kra")
    record = {
        "schema": "krita-agent-long-job/1",
        "id": identifier,
        "state": "ready_for_next_batch",
        "source_sha256": _digest(spec),
        "batch_steps": batch_steps,
        "batch_count": len(batches),
        "next_batch": 1,
        "completed": [{
            "index": 0,
            "job_id": "already-completed",
            "checkpoint": first_checkpoint,
            "batch_sha256": _digest(batches[0]),
            "steps": len(batches[0]),
        }],
        "current": None,
        "resume_count": 0,
        "policy": "no auto replay of uncertain native effects",
    }
    ledger.write(record)
    return ledger, record


def test_resume_continues_only_remaining_batches(tmp_path):
    spec = task(4)
    ledger, record = ready_ledger(tmp_path, spec)

    class CompletedClient:
        def __init__(self):
            self.submissions = []
            self.events = []
            self.restore_calls = 0

        def submit(self, steps):
            self.events.append("submit")
            self.submissions.append(steps)
            return {"id": "resumed-job"}

        def request(self, command, **params):
            if command == "checkpoint.restore":
                self.restore_calls += 1
                self.events.append("restore")
                assert params["id"] == record["completed"][-1]["checkpoint"]["id"]
                source = Path(record["completed"][-1]["checkpoint"]["path"])
                restored = tmp_path / "restored.kra"
                restored.write_bytes(source.read_bytes())
                return {"restored": {
                    "path": str(restored),
                    "document": "Resume fixture",
                }}
            assert command == "job.status"
            result = checkpoint(tmp_path / "batch-1.kra")
            return {"state": "completed", "done": 3, "last_result": result}

    client = CompletedClient()
    result = resume(client, spec, ledger.path, confirm=True)
    assert result["state"] == "completed"
    assert client.restore_calls == 1
    assert client.events == ["restore", "submit"]
    assert len(client.submissions) == 1
    assert client.submissions[0] == split_workflow(spec, 2)[1]
    saved = inspect_ledger(ledger.path)
    assert saved["resume_count"] == 1
    assert saved["next_batch"] == 2


def test_resume_requires_explicit_confirmation(tmp_path):
    spec = task(4)
    ledger, _ = ready_ledger(tmp_path, spec)
    with pytest.raises(ValueError, match="--confirm"):
        resume(object(), spec, ledger.path)


def test_resume_refuses_unknown_effects(tmp_path):
    spec = task(4)
    ledger, record = ready_ledger(tmp_path, spec)
    record["state"] = "unknown_needs_review"
    ledger.write(record)
    with pytest.raises(ValueError, match="completed-batch boundary"):
        resume(object(), spec, ledger.path, confirm=True)


def test_resume_refuses_changed_workflow(tmp_path):
    spec = task(4)
    ledger, _ = ready_ledger(tmp_path, spec)
    changed = task(4)
    changed["steps"][0]["parameters"]["name"] = "Changed"
    with pytest.raises(ValueError, match="differs"):
        resume(object(), changed, ledger.path, confirm=True)


def test_resume_refuses_tampered_checkpoint(tmp_path):
    spec = task(4)
    ledger, _ = ready_ledger(tmp_path, spec)
    (tmp_path / "batch-0.kra").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        resume(object(), spec, ledger.path, confirm=True)



def test_resume_refuses_prepared_ledger_without_checkpoint(tmp_path):
    spec = task(4)
    batches = split_workflow(spec, 2)
    identifier = uuid.uuid4().hex
    ledger = Ledger(tmp_path, identifier)
    ledger.write({
        "schema": "krita-agent-long-job/1",
        "id": identifier,
        "state": "prepared",
        "source_sha256": _digest(spec),
        "batch_steps": 2,
        "batch_count": len(batches),
        "next_batch": 0,
        "completed": [],
        "current": None,
    })
    with pytest.raises(ValueError, match="completed-batch boundary"):
        resume(object(), spec, ledger.path, confirm=True)


def test_ambiguous_checkpoint_restore_never_submits_or_retries(tmp_path):
    spec = task(4)
    ledger, _ = ready_ledger(tmp_path, spec)

    class LostRestore:
        restore_calls = 0
        submit_calls = 0

        def request(self, command, **params):
            assert command == "checkpoint.restore"
            self.restore_calls += 1
            raise TimeoutError("restore reply lost after possible document open")

        def submit(self, steps):
            self.submit_calls += 1
            return {"id": "must-not-submit"}

    client = LostRestore()
    result = resume(client, spec, ledger.path, confirm=True)
    assert result["state"] == "unknown_needs_review"
    assert client.restore_calls == 1
    assert client.submit_calls == 0
    saved = inspect_ledger(ledger.path)
    assert saved["state"] == "unknown_needs_review"
    with pytest.raises(ValueError, match="completed-batch boundary"):
        resume(client, spec, ledger.path, confirm=True)
    assert client.restore_calls == 1
