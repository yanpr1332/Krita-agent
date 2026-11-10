"""Pixel-grounded export and fresh-reopen evidence (no simulated Krita rendering).

Strict acceptance requires identical RGBA pixels. A separately reported, explicitly
bounded one-level RGB tolerance never promotes a failing strict comparison.
"""
import hashlib
import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image

MAX_PIXELS = 64_000_000
MAX_MERGED_BYTES = 256 * 1024 * 1024
MAX_XML_BYTES = 16 * 1024 * 1024
RGB_TOLERANCE = 1
CHANGED_PIXEL_RATIO_TOLERANCE = 0.0001


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _png_profile(image):
    icc = image.info.get("icc_profile")
    if not isinstance(icc, bytes):
        icc = None
    return {
        "mode": image.mode,
        "size": [image.width, image.height],
        "icc_sha256": hashlib.sha256(icc).hexdigest() if icc else None,
        "icc_bytes": len(icc) if icc else 0,
        "srgb_intent": image.info.get("srgb"),
        "gamma": image.info.get("gamma"),
    }


def _kra_merged(path):
    with zipfile.ZipFile(path) as archive:
        xml_entry = archive.getinfo("maindoc.xml")
        merged_entry = archive.getinfo("mergedimage.png")
        if xml_entry.file_size > MAX_XML_BYTES or merged_entry.file_size > MAX_MERGED_BYTES:
            raise ValueError("KRA metadata or merged image exceeds the inspection budget")
        root = ElementTree.fromstring(archive.read(xml_entry))
        attrs = {}
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1].lower() == "image":
                attrs = {key.lower(): value for key, value in node.attrib.items()}
                break
        merged = archive.read(merged_entry)
    return merged, {
        "color_model": attrs.get("colorspacename") or attrs.get("colormodel"),
        "color_depth": attrs.get("depth") or attrs.get("colordepth"),
        "profile_name": attrs.get("profile") or attrs.get("colorprofile"),
    }


def compare_rgba(original, other):
    """Bounded scan; count differing RGBA pixels, RGB deltas and alpha deltas."""
    a_size = [original.width, original.height]
    b_size = [other.width, other.height]
    result = {
        "original_size": a_size,
        "comparison_size": b_size,
        "dimensions_equal": a_size == b_size,
        "different_pixels": None,
        "rgb_different_pixels": None,
        "alpha_different_pixels": None,
        "max_channel_difference": None,
        "max_rgb_difference": None,
        "max_alpha_difference": None,
        "strict_match": False,
        "minor_color_tolerance": {
            "max_rgb_difference": RGB_TOLERANCE,
            "max_changed_pixel_ratio": CHANGED_PIXEL_RATIO_TOLERANCE,
            "max_alpha_difference": 0,
            "within_tolerance": False,
        },
    }
    if a_size != b_size or original.width * original.height > MAX_PIXELS:
        return result
    width, height = original.size
    different = rgb_different = alpha_different = 0
    max_rgb = max_alpha = 0
    for y in range(0, height, 128):
        box = (0, y, width, min(height, y + 128))
        aa = original.crop(box).convert("RGBA").tobytes()
        bb = other.crop(box).convert("RGBA").tobytes()
        for offset in range(0, len(aa), 4):
            rgb = max(abs(aa[offset + ch] - bb[offset + ch]) for ch in range(3))
            alpha = abs(aa[offset + 3] - bb[offset + 3])
            if rgb or alpha:
                different += 1
            if rgb:
                rgb_different += 1
                max_rgb = max(max_rgb, rgb)
            if alpha:
                alpha_different += 1
                max_alpha = max(max_alpha, alpha)
    result.update({
        "different_pixels": different,
        "rgb_different_pixels": rgb_different,
        "alpha_different_pixels": alpha_different,
        "max_channel_difference": max(max_rgb, max_alpha),
        "max_rgb_difference": max_rgb,
        "max_alpha_difference": max_alpha,
        "strict_match": different == 0,
    })
    result["minor_color_tolerance"]["within_tolerance"] = (
        max_rgb <= RGB_TOLERANCE and alpha_different == 0
        and different / (width * height) <= CHANGED_PIXEL_RATIO_TOLERANCE
    )
    return result


def export_integrity(kra_path, png_path):
    """Compare KRA embedded mergedimage.png with the initial Krita PNG export."""
    report = {
        "schema": "krita-agent-export-integrity/1",
        "kra_sha256": sha256(kra_path),
        "png_sha256": sha256(png_path),
        "status": "error",
        "pixels": None,
        "color_configuration": None,
    }
    try:
        merged, kra_color = _kra_merged(kra_path)
        with Image.open(io.BytesIO(merged)) as embedded, Image.open(png_path) as exported:
            pixels = compare_rgba(embedded, exported)
            colors = {"kra": kra_color, "embedded_png": _png_profile(embedded),
                      "export_png": _png_profile(exported)}
        report.update({
            "pixels": pixels,
            "color_configuration": colors,
            "status": "pass" if pixels["strict_match"] else "fail",
        })
    except Exception as exc:
        report["error"] = str(exc)
    return report


def reopen_stability(original_png, reopened_png, kra_sha256=None):
    """Compare a real fresh-KRA reopen export with the first PNG and its ICC data."""
    report = {
        "schema": "krita-agent-reopen-stability/1",
        "kra_sha256": kra_sha256,
        "png_sha256": sha256(original_png),
        "reopened_png_sha256": sha256(reopened_png),
        "status": "error",
        "pixels": None,
        "color_configuration": None,
    }
    try:
        with Image.open(original_png) as initial, Image.open(reopened_png) as fresh:
            pixels = compare_rgba(initial, fresh)
            first_color = _png_profile(initial)
            fresh_color = _png_profile(fresh)
        profile_keys = ("icc_sha256", "srgb_intent", "gamma", "mode")
        colors_match = all(first_color[key] == fresh_color[key] for key in profile_keys)
        report.update({
            "pixels": pixels,
            "color_configuration": {
                "original_png": first_color,
                "reopened_png": fresh_color,
                "consistent": colors_match,
            },
            "status": "pass" if pixels["strict_match"] and colors_match else "fail",
        })
    except Exception as exc:
        report["error"] = str(exc)
    return report
