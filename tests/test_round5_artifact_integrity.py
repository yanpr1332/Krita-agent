"""Offline integrity metrics; these fixtures do not simulate Krita acceptance."""
import io
import zipfile

from PIL import Image

from krita_agent.artifact_integrity import (
    compare_rgba, export_integrity, reopen_stability,
)


def _native_pair(tmp_path):
    png = tmp_path / "first.png"
    Image.new("RGBA", (100, 100), (50, 60, 70, 255)).save(png)
    kra = tmp_path / "drawing.kra"
    with zipfile.ZipFile(kra, "w") as archive:
        archive.writestr("maindoc.xml",
                         '<DOC><IMAGE colorspacename="RGBA" depth="U8" profile="sRGB"/></DOC>')
        archive.writestr("mergedimage.png", png.read_bytes())
    return kra, png


def test_export_integrity_captures_native_color_configuration(tmp_path):
    kra, png = _native_pair(tmp_path)
    result = export_integrity(kra, png)
    assert result["status"] == "pass"
    assert result["pixels"]["different_pixels"] == 0
    assert result["color_configuration"]["kra"] == {
        "color_model": "RGBA", "color_depth": "U8", "profile_name": "sRGB",
    }


def test_reopen_stability_counts_alpha_and_reports_tolerance_separately(tmp_path):
    kra, png = _native_pair(tmp_path)
    with Image.open(png) as original:
        other = original.copy()
    for x in range(5):
        other.putpixel((x, 0), (51, 60, 70, 255))
    other.putpixel((6, 0), (50, 60, 70, 254))
    reopened = tmp_path / "reopened.png"
    other.save(reopened)
    report = reopen_stability(png, reopened, "a" * 64)
    assert report["status"] == "fail"
    pixels = report["pixels"]
    assert pixels["different_pixels"] == 6
    assert pixels["rgb_different_pixels"] == 5
    assert pixels["alpha_different_pixels"] == 1
    assert pixels["max_channel_difference"] == 1
    assert pixels["minor_color_tolerance"]["within_tolerance"] is False


def test_minor_rgb_difference_is_not_a_strict_pass(tmp_path):
    kra, png = _native_pair(tmp_path)
    with Image.open(png) as original:
        other = original.copy()
    other.putpixel((0, 0), (51, 60, 70, 255))
    reopened = tmp_path / "reopened.png"
    other.save(reopened)
    result = reopen_stability(png, reopened)
    assert result["pixels"]["minor_color_tolerance"]["within_tolerance"] is True
    assert result["pixels"]["strict_match"] is False
    assert result["status"] == "fail"


def test_missing_or_different_size_is_strictly_rejected():
    original = Image.new("RGB", (12, 12), "red")
    other = Image.new("RGB", (11, 12), "red")
    metrics = compare_rgba(original, other)
    assert metrics["dimensions_equal"] is False
    assert metrics["strict_match"] is False


def test_matching_pixels_with_changed_icc_profile_fails_stability(tmp_path):
    original = tmp_path / "original.png"
    reopened = tmp_path / "reopened.png"
    image = Image.new("RGB", (20, 20), (40, 50, 60))
    image.save(original, icc_profile=b"test-profile-a")
    image.save(reopened, icc_profile=b"test-profile-b")
    result = reopen_stability(original, reopened)
    assert result["pixels"]["strict_match"] is True
    assert result["color_configuration"]["consistent"] is False
    assert result["status"] == "fail"
