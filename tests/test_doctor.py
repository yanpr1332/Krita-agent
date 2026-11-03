import subprocess
import unittest
from unittest.mock import patch
from pathlib import Path
from krita_agent.cli import inspect, main


class DoctorTests(unittest.TestCase):
    def test_missing_file(self):
        result = inspect("definitely-missing-krita.exe")
        self.assertFalse(result["exists"])
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["runtime_capabilities"], "not probed")

    @patch("krita_agent.cli.subprocess.run")
    def test_version_and_failure(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "Krita 5.3\n", "")
        self.assertEqual(inspect(__file__)["version"], "Krita 5.3")
        run.return_value = subprocess.CompletedProcess([], 1, "", "error")
        self.assertIsNotNone(inspect(__file__)["error"])
        run.side_effect = subprocess.TimeoutExpired("krita", 10)
        self.assertIsNotNone(inspect(__file__)["error"])


if __name__ == "__main__":
    unittest.main()
