"""Offline task compilation regression tests; no Krita required."""
import unittest
from krita_agent.protocol import TaskError, compile_task, points
from krita_agent.geometry import demo_task


class ProtocolTests(unittest.TestCase):
    def test_demo(self):
        steps = compile_task(demo_task())
        self.assertEqual(steps[0]["command"], "canvas.create")
        self.assertEqual(steps[-1]["command"], "document.export")
        self.assertTrue(any(s["command"] == "draw.stroke" for s in steps))

    def test_reject_nonfinite_or_invalid(self):
        with self.assertRaises(TaskError):
            points([{"x": float("nan"), "y": 2}])
        with self.assertRaises(TaskError):
            points([{"x": 0, "y": 0, "pressure": 2}])
        with self.assertRaises(TaskError):
            compile_task({"document": {"width": True, "height": 200}})
        with self.assertRaises(TaskError):
            compile_task({"document": {"width": 100, "height": 100},
                          "strokes": [{"points": [{"x": 1, "y": 2, "time_ms": 3},
                                                   {"x": 2, "y": 4, "time_ms": 1}]}]})

    def test_unsafe_filename(self):
        with self.assertRaises(TaskError):
            compile_task({"document": {"width": 100, "height": 100},
                          "output": {"kra": "../user.kra"}})

    def test_brush(self):
        task = {"document": {"width": 256, "height": 256},
                "brush": {"size": 15, "color": "#abcdef", "pressure_enabled": True}}
        self.assertEqual(compile_task(task)[2]["parameters"]["size"], 15)
