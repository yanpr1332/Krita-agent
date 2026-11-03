"""Offline Bézier and pressure curve tests."""
import unittest
from krita_agent.geometry import cubic_bezier


class GeometryTests(unittest.TestCase):
    def test_endpoints_and_pressure(self):
        path = cubic_bezier((0, 0), (50, 0), (50, 100), (100, 100), 11)
        self.assertEqual(len(path), 11)
        self.assertEqual(path[0]["x"], 0)
        self.assertEqual(path[-1]["y"], 100)
        self.assertGreater(path[5]["pressure"], path[0]["pressure"])
        self.assertGreater(path[5]["pressure"], path[-1]["pressure"])
