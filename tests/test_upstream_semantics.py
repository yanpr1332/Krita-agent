"""Not executed in Round 2: source evidence stays separate from runtime proof."""
import unittest
from krita_agent.upstream_semantics import enrich, ingest_probes


class SemanticsTests(unittest.TestCase):
    def test_classify_without_claiming_runtime(self):
        result = enrich({"candidates": [{"symbol": "paintPolylineStroke", "file": "libs/libkis/Node.h",
                                          "kind": "added", "source_url": "https://example.invalid"}]},
                        ingest_probes({"Next": {"symbols": {"StrokePoint": True}}}))
        self.assertIn("brush_stroke", result["impact"][0]["areas"])
        self.assertFalse(result["impact"][0]["runtime_verified"])
        self.assertEqual(result["capabilities_by_build"]["Next"]["StrokePoint"]["state"], "present_in_build")
