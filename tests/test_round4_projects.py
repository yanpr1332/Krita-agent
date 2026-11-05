"""Offline project provenance and immutable artifact tests."""
from pathlib import Path
import pytest
from krita_agent.projects import init,show,add,audit
from krita_agent.protocol_v2 import Capability,ErrorCode,ExecutionResult
from krita_agent.compatibility import assemble


def test_project_artifacts_hashed(tmp_path):
    init(tmp_path,"Landscape")
    sample=tmp_path/"reference.txt"
    sample.write_text("test")
    add(tmp_path,sample,"reference")
    assert show(tmp_path)["artifacts"][0]["sha256"]
    assert audit(tmp_path)["all_valid"] is True
    sample.write_text("tampered")
    assert audit(tmp_path)["all_valid"] is False


def test_evidence_does_not_promote_source_only():
    matrix=assemble({"Next":{"symbols":{"Node.paintLine":True,"NewAPI":False}}},
                    {"entries":[]})
    assert matrix["builds"]["Next"]["Node.paintLine"]["verified"] is False
    assert matrix["builds"]["Next"]["NewAPI"]["evidence"]=="not_supported"
    with pytest.raises(ValueError):
        Capability("Fake","Next","source_seen",verified=True)
    with pytest.raises(ValueError):
        ExecutionResult("failed","id",error_code=ErrorCode.UNKNOWN_EFFECT.value,
                        retry_safe=True)
