"""Source-level safety requirements for planned native regression."""
import json
from pathlib import Path

import pytest

from krita_agent.workflow import compile_workflow
from krita_agent.protocol import TaskError


def test_guarded_checkpoint_workflow_compiles():
    steps = compile_workflow({
        "steps": [
            {"command": "canvas.create", "parameters": {
                "width": 256, "height": 256, "name": "Test"}},
            {"command": "layer.create", "parameters": {"name": "Ink"}},
            {"command": "checkpoint.create", "parameters": {}},
        ]})
    assert steps[-1]["command"] == "checkpoint.create"


def test_unapproved_pixel_and_recovery_denied_in_workflow():
    for action in ("checkpoint.restore", "checkpoint.resume",
                   "pixel.transaction.patch", "pixel.transaction.undo",
                   "layer.delete", "document.close"):
        with pytest.raises(TaskError):
            compile_workflow({"steps": [{"command": action, "parameters": {"confirm": True}}]})


def test_workflow_never_overwrites_kra():
    with pytest.raises(TaskError):
        compile_workflow({"steps": [{
            "command": "document.save",
            "parameters": {"path": "test.kra", "overwrite": True}}]})
