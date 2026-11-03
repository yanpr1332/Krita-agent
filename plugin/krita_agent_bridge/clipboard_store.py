"""Bounded, same-user cross-session selection clipboard via output-root artifacts."""
import base64
import hashlib
import json
import os
import uuid
import zlib
from pathlib import Path
from .advanced_utils import integer, word

COMMANDS = frozenset(("clipboard.save", "clipboard.load", "clipboard.inspect"))
MAX_CLIP_PIXELS = 4000000


def _path(bridge, name, for_read=False):
    stem = word(name, "clipboard filename", 220)
    if not stem.endswith(".kclip"):
        raise ValueError("Clipboard filename must end with .kclip")
    target = (bridge.output_dir / "clips" / stem).resolve()
    allowed = (bridge.output_dir / "clips").resolve()
    if allowed not in target.parents or target == allowed:
        raise ValueError("Clipboard must stay inside output/clips")
    if for_read and not target.is_file():
        raise FileNotFoundError(target)
    if not for_read and target.exists():
        raise FileExistsError("Clipboard already exists")
    return target


def _decode(data, size):
    compressed = base64.b64decode(data.encode("ascii"), validate=True)
    decompressor = zlib.decompressobj()
    raw = decompressor.decompress(compressed, size + 1)
    if len(raw) > size or decompressor.unconsumed_tail:
        raise ValueError("Clipboard decompression limit exceeded")
    raw += decompressor.flush(size + 1 - len(raw))
    if len(raw) != size or not decompressor.eof:
        raise ValueError("Clipboard payload is invalid")
    return raw


def execute(bridge, command, p):
    path = _path(bridge, p.get("name"), command != "clipboard.save")
    if command == "clipboard.save":
        clip = getattr(bridge, "selection_clip", None)
        if clip is None:
            raise RuntimeError("Use selection.copy or selection.cut first")
        width, height, pixels = clip
        if width*height > MAX_CLIP_PIXELS or len(pixels) != width*height*4:
            raise ValueError("Clipboard outside safe RGBA U8 bounds")
        sha = hashlib.sha256(pixels).hexdigest()
        record = {"schema": 1, "width": width, "height": height, "sha256": sha,
                  "format": "BGRA_U8", "pixels_zlib_b64": base64.b64encode(zlib.compress(pixels)).decode("ascii")}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
        return {"path": str(path), "width": width, "height": height, "sha256": sha}
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema") != 1 or record.get("format") != "BGRA_U8":
        raise ValueError("Unsupported clipboard format")
    width = integer(record.get("width"), "width", 1, 16384)
    height = integer(record.get("height"), "height", 1, 16384)
    if width*height > MAX_CLIP_PIXELS:
        raise ValueError("Stored clipboard is too large")
    pixels = _decode(record["pixels_zlib_b64"], width*height*4)
    digest = hashlib.sha256(pixels).hexdigest()
    if digest != record.get("sha256"):
        raise ValueError("Clipboard integrity failure")
    if command == "clipboard.load":
        bridge.selection_clip = (width, height, pixels)
    return {"path": str(path), "width": width, "height": height,
            "sha256": digest, "loaded": command == "clipboard.load"}
