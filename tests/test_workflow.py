"""Not executed in Round 2: offline safe workflow checks."""
import unittest
from krita_agent.workflow import compile_workflow
from krita_agent.protocol import TaskError


class WorkflowTests(unittest.TestCase):
    def test_existing_document_revision(self):
        spec = {"steps": [
            {"command": "layer.select_id", "parameters": {"id": "selected-layer-id"}},
            {"command": "brush.configure", "parameters": {"size": 22}},
            {"command": "draw.stroke", "parameters": {"smooth": True, "points": [
                {"x": 20, "y": 30}, {"x": 40, "y": 40}, {"x": 50, "y": 50}]}},
            {"command": "preview.canvas", "parameters": {"filename": "previews/step-2.png"}}]}
        steps = compile_workflow(spec)
        self.assertEqual(len(steps), 4)
        self.assertNotIn("smooth", steps[2]["parameters"])
        self.assertEqual(steps[2]["command"], "draw.stroke")

    def test_denies_destructive_or_arbitrary(self):
        with self.assertRaises(TaskError):
            compile_workflow({"steps": [{"command": "layer.delete", "parameters": {"confirm": True}}]})
        with self.assertRaises(TaskError):
            compile_workflow({"steps": [{"command": "exec", "parameters": {"code": "pass"}}]})
        with self.assertRaises(TaskError):
            compile_workflow({"steps": [{"command": "document.export",
                                        "parameters": {"path": "x.png", "overwrite": True}}]})
