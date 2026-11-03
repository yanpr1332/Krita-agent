"""Local offline preview comparison and digest-based change detection.

The optional Pillow dependency provides pixel statistics; it does not send
images to external services. Comparisons can be part of a future planner.
"""
import hashlib
from pathlib import Path


def digest(filename):
    source = Path(filename)
    if not source.is_file():
        raise FileNotFoundError(str(source))
    sha = hashlib.sha256()
    size = 0
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(262144), b""):
            size += len(chunk)
            sha.update(chunk)
    return {"filename": str(source), "bytes": size, "sha256": sha.hexdigest()}


def compare(first, second, region=None):
    a, b = digest(first), digest(second)
    result = {"first": a, "second": b, "identical_bytes": a["sha256"] == b["sha256"],
              "pixel_comparison": "Pillow unavailable"}
    try:
        from PIL import Image, ImageChops, ImageStat, UnidentifiedImageError
    except ImportError:
        return result
    try:
        with Image.open(first) as original, Image.open(second) as revised:
            x = original.convert("RGBA")
            y = revised.convert("RGBA")
    except UnidentifiedImageError:
        result["pixel_comparison"] = "unsupported_image"
        return result
    if x.size != y.size:
        result.update(pixel_comparison="different_canvas_size",
                      first_size=list(x.size), second_size=list(y.size))
        return result
    if region is not None:
        if not isinstance(region, (list, tuple)) or len(region) != 4 or any(type(n) is not int for n in region):
            raise ValueError("region must be [x,y,width,height] integers")
        left, top, width, height = region
        if left < 0 or top < 0 or width < 1 or height < 1 or left+width > x.width or top+height > x.height:
            raise ValueError("region outside image")
        box = (left, top, left+width, top+height)
        x, y = x.crop(box), y.crop(box)
    rgba_diff = ImageChops.difference(x, y)
    channels = rgba_diff.split()
    mask = channels[0]
    for channel in channels[1:]:
        mask = ImageChops.lighter(mask, channel)
    diff = rgba_diff.convert("RGB")
    stat = ImageStat.Stat(diff)
    result.update(pixel_comparison="computed",
                  region=list(region) if region else None,
                  mean_absolute_rgb=[round(n, 5) for n in stat.mean],
                  changed_bbox=list(mask.getbbox()) if mask.getbbox() else None)
    return result
