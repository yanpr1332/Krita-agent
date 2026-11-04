"""Offline non-replaying durable long-job coordinator tests, not executed."""
import json
from pathlib import Path
import pytest
from krita_agent.scheduler import split_workflow,run,inspect_ledger
from krita_agent.protocol import TaskError


def task(n=450):
    return {"steps":[{"command":"layer.create","parameters":{"name":"Frame-"+str(i)}} for i in range(n)]}


def test_very_long_steps_split_with_checkpoints():
    batches=split_workflow(task(),batch_steps=90)
    assert len(batches)>4
    assert all(len(batch)<=91 for batch in batches)
    assert all(batch[-1]["command"]=="checkpoint.create" for batch in batches)
    assert sum(len(b)-1 for b in batches)==450


def test_unsupported_and_overlength_rejected():
    with pytest.raises(TaskError):
        split_workflow({"steps":[{"command":"shell","parameters":{}}]})
    with pytest.raises(TaskError):
        split_workflow(task(450),batch_steps=400)


def test_unknown_reply_does_not_retry(tmp_path):
    class LostReply:
        times=0
        def submit(self,steps):
            self.times+=1
            raise TimeoutError("Lost confirmation after possible native effect")
    client=LostReply()
    result=run(client,task(6),tmp_path,batch_steps=3)
    assert client.times==1
    assert result["state"]=="unknown_needs_review"
    saved=inspect_ledger(result["ledger"])
    assert saved["current"]["job_id"] is None
    assert saved["next_batch"]==0
