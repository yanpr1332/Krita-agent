"""Exercise native dispatch regressions without importing Krita or Qt."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest


def dispatcher(namespace):
    source = Path(__file__).parents[1] / "plugin/krita_agent_bridge/__init__.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "KritaAgentBridge")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_execute")
    module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
    exec(compile(module, str(source), "exec"), namespace)
    return namespace["_execute"]


def test_line_converts_float_coordinates_to_native_integer_points():
    node = Mock()
    class Point:
        def __init__(self, x, y): self.x, self.y = x, y
        def toPoint(self): return (round(self.x), round(self.y))
    execute = dispatcher({"Krita": SimpleNamespace(instance=lambda: None),
                          "QPointF": Point, "_number": lambda v, *args: float(v)})
    execute(SimpleNamespace(_node=lambda: node), "draw.line",
            dict(x1=1.2, y1=2.3, x2=3.4, y2=4.5))
    node.paintLine.assert_called_once_with((1, 2), (3, 4), 1.0, 1.0)


@pytest.mark.parametrize("failure", [False, True])
def test_export_restores_batchmode_even_on_failure(failure):
    doc = Mock()
    doc.batchmode.return_value = False
    if failure: doc.exportImage.side_effect = RuntimeError("export failed")
    else: doc.exportImage.return_value = True
    execute = dispatcher({"Krita": SimpleNamespace(instance=lambda: None), "InfoObject": object})
    bridge = SimpleNamespace(_safe_path=lambda *args: "test.png", _doc=lambda: doc)
    if failure:
        with pytest.raises(RuntimeError, match="export failed"):
            execute(bridge, "document.export", {"path": "test.png"})
    else:
        assert execute(bridge, "document.export", {"path": "test.png"})["format"] == "png"
    assert [c.args for c in doc.setBatchmode.call_args_list] == [(True,), (False,)]


def test_job_metrics_reaches_advanced_dispatch_instead_of_legacy_job_router():
    advanced = Mock(return_value={"metrics": {"last_step_ms": 1}})
    execute = dispatcher({"Krita": SimpleNamespace(instance=lambda: None),
                          "ADVANCED_COMMANDS": {"job.metrics"},
                          "dispatch_advanced": advanced})
    bridge = SimpleNamespace(_job=Mock(side_effect=AssertionError("legacy router used")))
    assert execute(bridge, "job.metrics", {"id": "job"})["metrics"]["last_step_ms"] == 1
    advanced.assert_called_once_with(bridge, "job.metrics", {"id": "job"})
