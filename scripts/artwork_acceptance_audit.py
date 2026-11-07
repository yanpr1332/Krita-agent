"""Artifact-only, fail-closed artwork acceptance auditor; not a visual judge."""
import argparse, hashlib, io, json, os, sys, uuid, zipfile
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from krita_agent.artwork_review import validate_human_review, validate_visual_review

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(262144),b""): h.update(b)
    return h.hexdigest()

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def audit(directory):
    run=Path(directory).expanduser().resolve()
    if (ROOT/"artwork-results").resolve() not in run.parents:
        raise ValueError("Run must live in repository-local artwork-results/<id>")
    contract=load(ROOT/"benchmarks/artwork/contracts/sunset_alpine_lake.v1.json")
    errors=[];checks=[]
    def test(name,ok,message):
        ok=bool(ok);checks.append({"name":name,"pass":ok})
        if not ok:errors.append(message)
    ref=ROOT/contract["reference"]["path"]
    test("benchmark_sha",ref.is_file() and sha(ref)==contract["reference"]["sha256"],"Benchmark reference changed")
    for rel in contract["output"]["required_filenames"]:
        target=(run/rel).resolve()
        test("artifact_"+rel,run in target.parents and target.is_file() and target.stat().st_size>0,
             "Missing/empty artifact: "+rel)
    final=run/"artwork.png"
    kra_path=run/"artwork.kra"
    final_sha=sha(final) if final.is_file() else None
    kra_sha=sha(kra_path) if kra_path.is_file() else None
    stage_paths=("stages/01-layout.png","stages/02-color.png","stages/03-final.png")
    stage_sha={rel:sha(run/rel) for rel in stage_paths if (run/rel).is_file()}
    size=None
    try:
        with Image.open(final) as im:
            size=(im.width,im.height)
            aspect=im.width/im.height
            test("image_pixel_budget",im.width*im.height<=64000000,
                 "Final artwork exceeds the 64-megapixel audit budget")
            test("image_size",im.width>=contract["output"]["minimum_width"]
                 and im.height>=contract["output"]["minimum_height"],"Final artwork too small")
            test("aspect_ratio",abs(aspect/(16/9)-1)<=contract["output"]["aspect_relative_tolerance"],
                 "Final artwork does not match benchmark aspect ratio")
    except Exception as exc:test("image_readable",False,str(exc))
    try:
        with zipfile.ZipFile(run/"artwork.kra") as kra:
            test("kra_manifest","maindoc.xml" in kra.namelist(),"KRA lacks maindoc.xml")
            native=kra.read("mergedimage.png")
        with Image.open(io.BytesIO(native)) as a,Image.open(final) as b:
            test("kra_png_match",a.convert("RGBA").tobytes()==b.convert("RGBA").tobytes()
                 and a.size==b.size,"Final PNG does not match native KRA mergedimage.png")
    except Exception as exc:test("kra_readable",False,str(exc))
    for rel in contract["output"]["required_filenames"]:
        if rel.endswith(".png") and (run/rel).exists():
            try:
                with Image.open(run/rel) as im:im.verify()
            except Exception as exc:test("readable_"+rel,False,str(exc))
    try:
        graph=load(run/"layer-graph.json")
        nodes=[n for n in graph["nodes"] if n.get("type")=="paintlayer"]
        test("paint_nodes",len(nodes)>=contract["output"]["min_nonempty_editable_paint_layers"],
             "Insufficient editable paint layers")
        if size:
            test("graph_size",(graph["document"]["width"],graph["document"]["height"])==size,
                 "KRA graph and PNG canvas differ")
        ids={n["id"] for n in nodes}
        layers=load(run/"layer-contributions.json")["layers"]
        real={l["node_id"] for l in layers if l.get("node_id") in ids
              and l.get("visible_contribution") is True
              and len(str(l.get("description","")).strip())>=8}
        test("painted_content_evidence",len(real)>=contract["output"]["min_nonempty_editable_paint_layers"],
             "Insufficient independently inspected visible layer contributions")
    except Exception as exc:test("graph_evidence",False,str(exc))
    try:
        execution=load(run/"execution.json")
        events=execution.get("commands",execution.get("steps",execution.get("events",[])))
        test("real_native_drawing",any(str(e.get("command",e.get("name",""))).startswith("draw.")
             for e in events if isinstance(e,dict)),"No recorded native painting steps")
        test("not_reference_copy",execution.get("imported_reference_as_final_artwork") is False,
             "Flattened reference import shortcut not ruled out")
    except Exception as exc:test("execution",False,str(exc))
    required=[o["key"] for o in contract["subject"]["required_objects"]]
    try:
        review=load(run/"reviews/visual-model.json")
        result=validate_visual_review(
            review, required, contract["subject"]["required_relations"],
            contract["reference"]["sha256"], final_sha, kra_sha, stage_sha,
        )
        test("independent_visual_review",result["valid"],
             "; ".join(result["errors"]) if result["errors"] else "Visual review is bound to the exact run artifacts")
    except Exception as exc:
        test("independent_visual_review",False,str(exc))
    try:
        human=load(run/"reviews/human.json")
        result=validate_human_review(human,final_sha,kra_sha,required)
        test("independent_human_review",result["valid"],
             "; ".join(result["errors"]) if result["errors"] else "Human review is bound to the exact run artifacts")
    except Exception as exc:
        test("independent_human_review",False,str(exc))
    report={"schema":"krita-agent-artwork-audit/2","run_id":run.name,
            "artwork_sha256":final_sha,"artwork_kra_sha256":kra_sha,
            "stage_preview_sha256":stage_sha,"status":"pass" if not errors else "fail",
            "checks":checks,"errors":errors,
            "note":"Only artifact consistency; a reviewer must actually inspect the painting"}
    tmp=run/("audit."+uuid.uuid4().hex+".tmp")
    tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    os.replace(tmp,run/"audit.json")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--run-dir",required=True)
    args=p.parse_args()
    try:
        result=audit(args.run_dir);print(json.dumps(result,ensure_ascii=False,indent=2))
        sys.exit(0 if result["status"]=="pass" else 1)
    except Exception as exc:
        print("Audit not complete:",exc,file=sys.stderr);sys.exit(2)
