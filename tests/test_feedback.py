"""Not executed in Round 2: hashing requires no Pillow installation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from krita_agent.feedback import digest, compare


def test_distinct_files_detected():
    with TemporaryDirectory() as folder:
        a, b = Path(folder)/"a.bin", Path(folder)/"b.bin"
        a.write_bytes(b"a")
        b.write_bytes(b"b")
        assert digest(a)["sha256"] != digest(b)["sha256"]
        assert compare(a, b)["identical_bytes"] is False
