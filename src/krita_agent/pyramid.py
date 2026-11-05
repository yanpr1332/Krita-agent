"""Offline tile pyramid PNG builder for large Krita previews; no Krita session."""
import hashlib
import json
from pathlib import Path
from .large_canvas import image_metadata,tiles,pyramid_layout


def _sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as stream:
        for buf in iter(lambda:stream.read(262144),b""):
            h.update(buf)
    return h.hexdigest()


def build(image_file,output_dir,tile_size=512):
    """Create 512/1024px tiles and index. New directory required (no overwrite)."""
    from PIL import Image
    meta=image_metadata(image_file)
    width,height=meta["size"]
    layout=pyramid_layout(width,height,tile_size)
    root=Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True,exist_ok=False)
    manifest={"schema":"krita-agent-pyramid/1","source":meta,
              "tile_size":tile_size,"levels":[],"color_management":"Embedded ICC is copied when available; no colorimetric test claimed"}
    with Image.open(meta["path"]) as source:
        icc=source.info.get("icc_profile")
        current=source.convert("RGBA")
        for level in layout:
            if current.size!=(level["width"],level["height"]):
                current=current.resize((level["width"],level["height"]),
                                      Image.Resampling.LANCZOS)
            rows=[]
            for x,y,w,h in tiles(*current.size,tile_size):
                filename="L"+str(level["level"])+"_"+str(x)+"_"+str(y)+".png"
                target=root/filename
                chunk=current.crop((x,y,x+w,y+h))
                arguments={"icc_profile":icc} if icc else {}
                chunk.save(target,format="PNG",**arguments)
                rows.append({"file":filename,"origin":[x,y],"size":[w,h],
                             "sha256":_sha(target)})
            manifest["levels"].append({"level":level["level"],
                "width":current.width,"height":current.height,"tiles":rows})
    with (root/"manifest.json").open("x",encoding="utf-8") as f:
        json.dump(manifest,f,indent=2,ensure_ascii=False)
    return {"root":str(root),"manifest":str(root/"manifest.json"),
            "levels":len(manifest["levels"]),"tile_count":sum(len(x["tiles"]) for x in manifest["levels"])}


def inspect(path):
    root=Path(path).expanduser().resolve()
    result=json.loads(root.read_text(encoding="utf-8"))
    if result.get("schema")!="krita-agent-pyramid/1":
        raise ValueError("Wrong pyramid schema")
    return {"source":result["source"],"levels":len(result["levels"]),
            "tile_count":sum(len(x["tiles"]) for x in result["levels"])}
