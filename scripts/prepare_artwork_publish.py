"""Create curated upload staging files; never git-commit or push automatically."""
import argparse,hashlib,json,sys
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))

def prepare(run_dir):
    run=Path(run_dir).expanduser().resolve()
    if (ROOT/"artwork-results").resolve() not in run.parents:
        raise ValueError("Run must be inside artwork-results")
    report=load(run/"audit.json")
    final=run/"artwork.png"
    if report.get("status")!="pass" or report.get("run_id")!=run.name:
        raise ValueError("Passed artifact audit for this run is required")
    if sha(final)!=report.get("artwork_sha256"):
        raise ValueError("Artwork changed after audit")
    if any(load(run/p).get("decision")!="pass" for p in
           ("reviews/human.json","reviews/visual-model.json")):
        raise ValueError("Independent reviewer did not approve")
    dest=ROOT/"docs/acceptance-evidence/artwork"/run.name
    dest.mkdir(parents=True,exist_ok=False)
    with Image.open(final) as src:
        preview=src.convert("RGB");preview.thumbnail((1600,1600),Image.Resampling.LANCZOS)
        preview.save(dest/"preview.jpg",quality=85,optimize=True)
    summary={"schema":"krita-agent-artwork-public/1","run_id":run.name,
             "original_png_sha256":sha(final),"preview_sha256":sha(dest/"preview.jpg"),
             "audit_status":"pass","visual_review":"pass","human_review":"pass",
             "kra":"retained_locally","cloud_uploaded":False}
    (dest/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    (dest/"README.md").write_text(
        "# Artwork result "+run.name+"\n\nOriginal editable KRA and full run "
        "evidence remain in the local artwork-results directory. "
        "Review this curated preview for privacy before manually committing or pushing.\n",
        encoding="utf-8")
    return {"staged_path":str(dest),"cloud_uploaded":False}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--run-dir",required=True)
    args=p.parse_args()
    try:print(json.dumps(prepare(args.run_dir),indent=2))
    except Exception as exc:print("Publish staging refused:",exc,file=sys.stderr);sys.exit(2)
