"""Artifact-only, fail-closed artwork acceptance auditor; not a visual judge."""
import argparse, hashlib, io, json, os, sys, uuid, zipfile
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

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
    final_sha=sha(final) if final.is_file() else None
    size=None
    try:
        with Image.open(final) as im:
            size=(im.width,im.height)
            aspect=im.width/im.height
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
    try:
        review=load(run/"reviews/visual-model.json")
        required=[o["key"] for o in contract["subject"]["required_objects"]]
        relations={r.get("description"):r.get("passes") for r in review.get("relations",[])}
        valid=(review.get("schema")=="krita-agent-artwork-vlm/1" and
               review.get("decision")=="pass" and review.get("coherent_full_scene") is True and
               bool(str(review.get("model","")).strip()) and
               review.get("reference_sha256")==contract["reference"]["sha256"] and
               review.get("artwork_png_sha256")==final_sha and
               all(review.get("objects",{}).get(k) is True for k in required) and
               all(relations.get(k) is True for k in contract["subject"]["required_relations"]))
        test("independent_visual_review",valid,"Visual review incomplete, negative or not bound to actual pixels")
    except Exception as exc:test("independent_visual_review",False,str(exc))
    try:
        human=load(run/"reviews/human.json")
        valid=(human.get("schema")=="krita-agent-artwork-human/1" and
               human.get("decision")=="pass" and human.get("artwork_png_sha256")==final_sha and
               human.get("coherent_full_scene") is True and
               human.get("all_required_objects_recognizable") is True and
               human.get("kra_reopened_and_viewed") is True and
               bool(str(human.get("reviewer","")).strip()) and
               len(str(human.get("observations","")).strip())>=20)
        test("independent_human_review",valid,"Human review incomplete or negative")
    except Exception as exc:test("independent_human_review",False,str(exc))
    report={"schema":"krita-agent-artwork-audit/1","run_id":run.name,
            "artwork_sha256":final_sha,"status":"pass" if not errors else "fail",
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
