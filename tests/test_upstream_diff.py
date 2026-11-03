"""Local synthetic Git source-change test; no network."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from krita_agent.upstream import compare, markdown_report, capability_matrix


class DiffTests(unittest.TestCase):
    def test_new_and_changed_signatures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.run(["git", "-C", str(root), *args], check=True,
                                      capture_output=True, text=True).stdout.strip()
            git("init")
            src = root / "libs" / "libkis"
            src.mkdir(parents=True)
            header = src / "Node.h"
            header.write_text("void paintLine(int x);\n", encoding="utf-8")
            git("add", ".")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "-m", "baseline")
            baseline = git("rev-parse", "HEAD")
            header.write_text("void paintLine(int x, int y);\nvoid paintPolylineStroke(int count);\n",
                              encoding="utf-8")
            git("add", ".")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "-m", "feature")
            result = compare(directory, baseline)
            symbols = {x["symbol"]: x["kind"] for x in result["candidates"]}
            self.assertEqual(symbols["paintLine"], "signature_or_implementation_changed")
            self.assertEqual(symbols["paintPolylineStroke"], "added")
            self.assertIn("source_seen", markdown_report(result))

    def test_capability_matrix_is_not_test_claim(self):
        matrix = capability_matrix({"Next": {"StrokePoint": True}})
        self.assertEqual(matrix["Next"]["StrokePoint"]["state"], "present_in_build")
        self.assertFalse(matrix["Next"]["StrokePoint"]["tested_working"])


class FetchFailureTests(unittest.TestCase):
    def test_failed_fetch_preserves_baseline_even_with_update(self):
        from krita_agent.upstream import initialize, check
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.run(["git", "-C", str(root), *args], check=True,
                                      capture_output=True, text=True).stdout.strip()
            git("init")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "--allow-empty", "-m", "baseline")
            git("remote", "add", "origin", str(root / "missing-remote.git"))
            baseline = root / "baseline.json"
            initialize(root, baseline)
            before = baseline.read_bytes()
            with self.assertRaises(subprocess.CalledProcessError):
                check(root, baseline, fetch=True, update=True)
            self.assertEqual(baseline.read_bytes(), before)
