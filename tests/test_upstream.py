import subprocess
import tempfile
import unittest
from pathlib import Path
from krita_agent.upstream import snapshot


class SnapshotTests(unittest.TestCase):
    def test_snapshot_and_dirty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                subprocess.run(["git", "-C", directory, *args], check=True, capture_output=True)
            git("init")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-m", "baseline")
            result = snapshot(directory)
            self.assertEqual(len(result["commit"]), 40)
            self.assertFalse(result["dirty"])
            Path(directory, "new.txt").write_text("new")
            self.assertTrue(snapshot(directory)["dirty"])

    def test_non_repository_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(subprocess.CalledProcessError):
                snapshot(directory)
