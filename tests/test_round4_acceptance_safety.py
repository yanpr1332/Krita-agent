"""Failure injection for uncertain native effects and storage integrity."""
import hashlib
from unittest.mock import Mock, patch

import pytest

from krita_agent import compatibility, scheduler
from krita_agent.document_graph import rebind


def graph(ids):
    return {
        "schema": "krita-agent-document-graph/1",
        "document": {"width": 1, "height": 1},
        "nodes": [
            {"id": identifier, "path": [0], "name": "Ink", "type": "paintlayer"}
            for identifier in ids
        ],
    }


@pytest.mark.parametrize("before,after", [(graph(["a"]), graph(["b", "c"])), (graph(["a", "b"]), graph(["c"]))])
def test_ambiguous_structural_keys_never_rebind(before, after):
    assert all(row["new_id"] is None for row in rebind(before, after)["mapping"])


def test_disk_full_before_submit_has_zero_remote_effects(tmp_path):
    client = Mock()
    workflow = {"steps": [{"command": "document.info", "parameters": {}}]}
    with patch.object(scheduler.Ledger, "write", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            scheduler.run(client, workflow, tmp_path)
    client.submit.assert_not_called()


def test_partial_ledger_failure_after_submit_never_retries(tmp_path):
    original = scheduler.Ledger.write
    calls = 0

    def fail_once(self, value):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("injected partial journal failure")
        return original(self, value)

    client = Mock()
    client.submit.return_value = {"id": "accepted-job"}
    workflow = {"steps": [{"command": "document.info", "parameters": {}}]}
    with patch.object(scheduler.Ledger, "write", fail_once):
        result = scheduler.run(client, workflow, tmp_path)

    assert client.submit.call_count == 1
    assert result["state"] == "unknown_needs_review"
    assert scheduler.inspect_ledger(result["ledger"])["state"] == "unknown_needs_review"


def test_capability_evidence_must_still_match_sha(tmp_path):
    evidence = tmp_path / "proof.json"
    evidence.write_text('{"passed":true}', encoding="utf-8")
    registry = {
        "entries": [{
            "build": "Build",
            "symbol": "API",
            "state": "tested_working",
            "reviewer_confirmed": True,
            "evidence_path": str(evidence),
            "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        }],
    }
    probes = {"Build": {"API": True}}

    assert compatibility.assemble(probes, registry)["builds"]["Build"]["API"]["verified"]
    evidence.write_text("tampered", encoding="utf-8")
    assert not compatibility.assemble(probes, registry)["builds"]["Build"]["API"]["verified"]
