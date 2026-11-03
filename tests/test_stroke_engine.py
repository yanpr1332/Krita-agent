"""Not executed in Round 2: planned deterministic regression cases."""
import unittest
from krita_agent.stroke_engine import resample, smooth, catmull_rom, plan_stroke
from krita_agent.protocol import TaskError


PATH = [{"x": 0, "y": 0, "pressure": 0.1, "time_ms": 0},
        {"x": 100, "y": 20, "pressure": 1.0, "time_ms": 100},
        {"x": 200, "y": 0, "pressure": 0.1, "time_ms": 200}]


class StrokeEngineTests(unittest.TestCase):
    def test_resample_endpoints(self):
        result = resample(PATH, spacing=5)
        self.assertEqual(result[0]["x"], 0)
        self.assertEqual(result[-1]["x"], 200)
        self.assertTrue(all(0 <= p["pressure"] <= 1 for p in result))
        self.assertEqual(result[-1]["time_ms"], 200)

    def test_smoothing_preserves_endpoints_and_pressure(self):
        result = smooth(PATH)
        self.assertEqual(result[0]["x"], 0)
        self.assertEqual(result[1]["pressure"], 1)
        self.assertEqual(result[-1]["y"], 0)

    def test_spline_sensors(self):
        result = catmull_rom(PATH)
        self.assertGreater(len(result), len(PATH))
        self.assertEqual(result[0]["pressure"], 0.1)

    def test_invalid_inputs(self):
        with self.assertRaises(TaskError):
            resample(PATH, spacing=0)
        with self.assertRaises(TaskError):
            plan_stroke({"points": PATH, "spline": True, "samples_per_segment": 5000})
