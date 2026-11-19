"""Round 10 — rights-gated, reproducible, offline visual reference analysis.

This module reads authorized local reference pixels; it NEVER sends images to
a model API, pastes them into native artwork, or claims to recognize objects.
Only bounded thumbnail color/value/edge measurements are reported.
"""
import hashlib
import math
from collections import Counter
from pathlib import Path

from .protocol import TaskError, integer, label, number
from .scene_v3 import digest

SCHEMA = "krita-agent-references/1"
ROLES = frozenset(("composition", "palette", "material", "structure", "technique"))
RIGHTS = frozenset(("owned", "public_domain", "licensed", "explicit_permission"))
EXTS = frozenset((".png", ".jpg", ".jpeg", ".webp"))
MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 16_000_000


def _check_map(value, allowed, name):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise TaskError("Invalid " + name + " object or unsupported fields")
    return value


def _check_id(value, name):
    import re
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,23}", value):
        raise TaskError("Invalid " + name)
    return value


def _rect(value):
    if not isinstance(value, list) or len(value) != 4:
        raise TaskError("Reference region must be normalized [x,y,w,h]")
    coords = [number(v, "region coordinate", 0, 1) for v in value]
    x, y, w, h = coords
    if w < .02 or h < .02 or x + w > 1.000001 or y + h > 1.000001:
        raise TaskError("Reference region is empty or outside image")
    return coords


def validate_reference_manifest(value):
    """Normalize author-declared usage/ROI; no file access and no rights inference."""
    _check_map(value, ("schema", "sources"), "reference manifest")
    if value.get("schema") != SCHEMA:
        raise TaskError("Unknown reference manifest schema")
    raw = value.get("sources")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 4:
        raise TaskError("Reference manifest requires 1..4 sources")
    sources, ids, owners = [], set(), {}
    for item in raw:
        _check_map(item, ("id", "file", "rights", "roles", "regions"), "source")
        sid = _check_id(item.get("id"), "source ID")
        if sid in ids:
            raise TaskError("Duplicate reference source ID")
        ids.add(sid)
        filename = item.get("file")
        if (not isinstance(filename, str) or not filename or len(filename) > 180
                or "\x00" in filename or "\\" in filename):
            raise TaskError("Unsafe reference filename")
        path = Path(filename)
        if path.is_absolute() or len(path.parts) != 1 or path.suffix.lower() not in EXTS:
            raise TaskError("Reference filename must be a single local image basename")
        rights = _check_map(item.get("rights"), ("basis", "permission_confirmed",
                                                 "source_note", "external_upload_permitted"), "reference rights")
        if (rights.get("basis") not in RIGHTS or rights.get("permission_confirmed") is not True
                or type(rights.get("external_upload_permitted", False)) is not bool):
            raise TaskError("Reference requires explicit right-to-use confirmation")
        note = label(rights.get("source_note"), "source rights note", 180)
        roles = item.get("roles")
        if not isinstance(roles, list) or not 1 <= len(roles) <= 4 or (
                len(set(roles)) != len(roles)) or set(roles) - ROLES:
            raise TaskError("Reference roles must be 1..4 distinct allowed roles")
        for role in roles:
            if role in ("composition", "palette", "structure"):
                if role in owners:
                    raise TaskError("Ambiguous multi-reference controller for " + role)
                owners[role] = sid
        regions, region_ids = [], set()
        for roi in item.get("regions", []):
            _check_map(roi, ("id", "rect", "subject_id", "material"), "reference ROI")
            rid = _check_id(roi.get("id"), "reference ROI ID")
            if rid in region_ids:
                raise TaskError("Duplicate reference ROI")
            region_ids.add(rid)
            subj = roi.get("subject_id")
            if subj is not None:
                subj = _check_id(subj, "ROI subject ID")
            regions.append({
                "id": rid, "rect": _rect(roi.get("rect")), "subject_id": subj,
                "material": label(roi["material"], "ROI material", 64)
                    if roi.get("material") is not None else None,
            })
        if len(regions) > 12:
            raise TaskError("Reference has more than 12 regions")
        sources.append({
            "id": sid, "file": filename,
            "rights": {"basis": rights["basis"], "permission_confirmed": True,
                       "source_note": note,
                       "external_upload_permitted": rights.get("external_upload_permitted", False)},
            "roles": sorted(roles), "regions": regions,
        })
    return {"schema": SCHEMA, "sources": sources}


def _safe_image(root, filename):
    root = Path(root).expanduser().resolve()
    path = root / filename
    if not root.is_dir() or path.is_symlink() or not path.is_file():
        raise TaskError("Reference file missing or links/unsafe path")
    if path.resolve().parent != root:
        raise TaskError("Reference must remain within authorized input directory")
    if not 0 < path.stat().st_size <= MAX_BYTES:
        raise TaskError("Reference exceeds 8 MiB source budget")
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise TaskError("Pillow>=10 is required for offline reference analysis") from exc
    try:
        with Image.open(path) as image:
            if image.width * image.height > MAX_PIXELS:
                raise TaskError("Reference exceeds 16 megapixels")
            if image.format not in ("PNG", "JPEG", "WEBP"):
                raise TaskError("Unsupported actual image format")
            image.load()
            rotated = ImageOps.exif_transpose(image)
            rgb = rotated.convert("RGB")
            rgb.thumbnail((384, 384))
            if rgb.width * rgb.height > 384 * 384:
                raise TaskError("Reference thumbnail exceeds budget")
            size = [image.width, image.height]
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise TaskError("Unreadable/unsafe reference image") from exc
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            hasher.update(chunk)
    return rgb, size, hasher.hexdigest()


def _pixels(image):
    return image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()


def _measure(image):
    """Coarse color statistics, not semantic segmentation or inferred technique."""
    image = image.convert("RGB")
    pixels = list(_pixels(image))
    if not pixels:
        raise TaskError("Empty reference image")
    n = len(pixels)
    means = [round(sum(p[c] for p in pixels) / n, 2) for c in range(3)]
    lum = [0] * 5
    buckets = Counter()
    for r, g, b in pixels:
        value = .2126 * r + .7152 * g + .0722 * b
        lum[min(4, int(value / 51.2))] += 1
        buckets[(r // 32, g // 32, b // 32)] += 1
    palette = []
    for (r, g, b), count in sorted(buckets.items(), key=lambda x: (-x[1], x[0]))[:6]:
        palette.append({
            "hex": "#%02X%02X%02X" % (min(255, r*32+16),
                                         min(255, g*32+16), min(255, b*32+16)),
            "share": round(count/n, 4),
        })
    gray = image.convert("L")
    gray.thumbnail((96, 96))
    w, h = gray.size
    pix = gray.load()
    active = total = 0
    for y in range(h-1):
        for x in range(w-1):
            total += 1
            if max(abs(pix[x,y] - pix[x+1,y]),
                   abs(pix[x,y] - pix[x,y+1])) >= 24:
                active += 1
    return {
        "mean_rgb": means,
        "value_fractions": [round(c/n, 4) for c in lum],
        "dominant_palette": palette,
        "edge_density_proxy": round(active / max(1, total), 4),
        "method": "RGB 32-level histogram, luminance quintiles, grayscale local difference",
        "semantic_objects_detected": False,
        "stroke_technique_inferred": False,
    }


def analyze_references(root, manifest):
    """Read exact authorized pixels, emit hash-bound metadata without image bytes."""
    normalized = validate_reference_manifest(manifest)
    reports = []
    for source in normalized["sources"]:
        thumbnail, original_size, sha = _safe_image(root, source["file"])
        regions = []
        for r in source["regions"]:
            x, y, w, h = r["rect"]
            left = min(thumbnail.width-1, int(x * thumbnail.width))
            top = min(thumbnail.height-1, int(y * thumbnail.height))
            right = max(left+1, min(thumbnail.width, math.ceil((x+w)*thumbnail.width)))
            bottom = max(top+1, min(thumbnail.height, math.ceil((y+h)*thumbnail.height)))
            region = thumbnail.crop((left,top,right,bottom))
            regions.append({
                "id": r["id"], "rect": r["rect"], "subject_id": r["subject_id"],
                "material": r["material"], "measurements": _measure(region),
            })
        reports.append({
            "source_id": source["id"], "sha256": sha, "pixel_dimensions": original_size,
            "rights": source["rights"], "roles": source["roles"],
            "global_measurements": _measure(thumbnail), "regions": regions,
        })
    result = {
        "schema": "krita-agent-reference-analysis/1", "manifest_sha256": digest(normalized),
        "sources": reports,
        "limits": {"visual_semantics": "not_inferred",
                   "model_api": "not_called", "artwork_acceptance": "not_established"},
    }
    result["analysis_sha256"] = digest(result)
    return result
