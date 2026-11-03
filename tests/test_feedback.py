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

def test_alpha_only_changes_are_detected(tmp_path):
    import pytest
    Image = pytest.importorskip('PIL.Image')
    a, b = tmp_path/'a.png', tmp_path/'b.png'
    Image.new('RGBA', (2, 2), (20, 30, 40, 0)).save(a)
    Image.new('RGBA', (2, 2), (20, 30, 40, 255)).save(b)
    result = compare(a, b)
    assert result['changed_bbox'] == [0, 0, 2, 2]
    assert result['mean_absolute_rgb'] == [0.0, 0.0, 0.0]
