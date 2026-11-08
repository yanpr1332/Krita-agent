"""Auditable multi-stage creative workflow with explicit side-effect boundaries.

No phase auto-replays native drawing. An interrupted paint, export or revision
is UNKNOWN and must be inspected manually; work-in-progress artifacts are kept.
"""
import hashlib
import json
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .creative_director import compile_approved, propose, validate_brief
from .creative_reviser import execute_revision, plan_revision, validate_revision
from .protocol import TaskError
from .scene_v3 import SCHEMA, digest, validate_scene
from .scheduler import run as run_longjob
from .visual_critic import critique

WORKFLOW_SCHEMA = "krita-agent-creative-workflow/1"
KNOWN_STATES = frozenset({
    "initialized", "planned", "plan_approved", "painting_unknown",
    "awaiting_export", "export_unknown", "awaiting_critique", "awaiting_revision_proposal",
    "revision_proposed", "revision_approved", "revision_unknown",
    "ready_for_delivery", "delivery_prepared", "review_blocked",
    "unknown_needs_review",
})


def _sha(path):
    digest_value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest_value.update(block)
    return digest_value.hexdigest()


def _time():
    return datetime.now(timezone.utc).isoformat()


def _write_new(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())


def _atomic(path, value):
    path = Path(path)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class CreativeWorkflow:
    def __init__(self, directory):
        self.root = Path(directory).expanduser().resolve()
        self.manifest = self.root / "creative-workflow.json"

    @classmethod
    def create(cls, directory, brief):
        spec = validate_brief(brief)
        instance = cls(directory)
        instance.root.mkdir(parents=True, exist_ok=False)
        record = {
            "schema": WORKFLOW_SCHEMA, "id": uuid.uuid4().hex,
            "status": "initialized", "created_at": _time(),
            "brief": spec, "version": 0,
            "artifacts": {}, "history": [{"at": _time(), "event": "initialized"}],
            "policy": "native effects never replayed automatically; final artwork needs human acceptance",
        }
        _write_new(instance.manifest, record)
        return instance

    def read(self):
        value = json.loads(self.manifest.read_text(encoding="utf-8"))
        if value.get("schema") != WORKFLOW_SCHEMA or value.get("status") not in KNOWN_STATES:
            raise TaskError("Invalid creative workflow manifest")
        return value

    def _save(self, record, event):
        record["history"].append({"at": _time(), "event": event})
        _atomic(self.manifest, record)

    def _expect(self, record, *states):
        if record["status"] not in states:
            raise TaskError("Workflow is in state {}; expected {}".format(
                record["status"], "/".join(states)
            ))

    def plan(self, provider=None, candidate=None, reference=None, profile_directory=None, build=None):
        record = self.read()
        self._expect(record, "initialized")
        if (provider is None) == (candidate is None):
            raise TaskError("Choose exactly one provider or manually supplied ScenePlan v3")
        if provider is not None:
            proposal = propose(record["brief"], provider, reference)
        else:
            scene = validate_scene(candidate)
            if (scene["document"]["width"], scene["document"]["height"]) != (
                record["brief"]["width"], record["brief"]["height"]
            ):
                raise TaskError("Scene differs from the approved canvas dimensions")
            proposal = {
                "schema": "krita-agent-creative-proposal/1", "scene": scene,
                "scene_sha256": digest(scene), "provider_model": "human_supplied",
                "approval": "required", "side_effects": "none",
            }
        compiled = compile_approved(
            proposal, profile_directory, build,
            preview_prefix="r5-runs/" + record["id"],
        )
        _write_new(self.root / "scene-plan-v3.json", proposal["scene"])
        _write_new(self.root / "creative-proposal.json", proposal)
        _write_new(self.root / "compiled-scene.json", compiled)
        record["artifacts"]["scene"] = {
            "path": "scene-plan-v3.json", "sha256": _sha(self.root / "scene-plan-v3.json"),
        }
        record["artifacts"]["compiled"] = {
            "path": "compiled-scene.json", "sha256": _sha(self.root / "compiled-scene.json"),
        }
        record["status"] = "planned"
        self._save(record, "plan_proposed")
        return {"status": record["status"], "plan_sha256": compiled["native_steps_sha256"],
                "objects": len(compiled["objects"]), "native_steps": len(compiled["steps"])}

    def approve_plan(self, confirm=False):
        if confirm is not True:
            raise TaskError("Explicit plan approval required")
        record = self.read()
        self._expect(record, "planned")
        compiled = json.loads((self.root / "compiled-scene.json").read_text(encoding="utf-8"))
        scene = json.loads((self.root / "scene-plan-v3.json").read_text(encoding="utf-8"))
        if (_sha(self.root / "compiled-scene.json") != record["artifacts"]["compiled"]["sha256"]
            or _sha(self.root / "scene-plan-v3.json") != record["artifacts"]["scene"]["sha256"]
            or digest(validate_scene(scene)) != compiled.get("source_sha256")):
            raise TaskError("Approved plan changed since it was compiled")
        record["status"] = "plan_approved"
        self._save(record, "plan_approved_by_user")
        return {"status": record["status"], "plan_sha256": compiled["native_steps_sha256"]}

    def paint(self, client, ledger_directory=None, batch_steps=120):
        record = self.read()
        self._expect(record, "plan_approved")
        compiled_path = self.root / "compiled-scene.json"
        if _sha(compiled_path) != record["artifacts"]["compiled"]["sha256"]:
            raise TaskError("Compiled plan changed after approval")
        plan = json.loads(compiled_path.read_text(encoding="utf-8"))
        record["status"] = "painting_unknown"
        self._save(record, "native_paint_submission_intent")
        result = run_longjob(
            client, {"steps": plan["steps"]},
            ledger_directory or self.root / "job-ledgers",
            batch_steps=batch_steps,
        )
        record["painting_result"] = result
        record["status"] = (
            "awaiting_export" if result.get("state") == "completed" else "unknown_needs_review"
        )
        self._save(record, "native_paint_" + result.get("state", "unknown"))
        return {"status": record["status"], "native": result}

    def export_native(self, client):
        """Save/export via authenticated Krita and archive immutable copies.

        Never retry after an uncertain result. The user may instead call
        record_artwork with files exported independently and verified on disk.
        """
        record = self.read()
        self._expect(record, "awaiting_export")
        tag = record["id"] + "-v" + str(record["version"] + 1)
        record["status"] = "export_unknown"
        self._save(record, "native_export_intent")
        try:
            kra = client.request("document.save", path="r5-artwork/" + tag + ".kra",
                                 overwrite=False)
            png = client.request("document.export", path="r5-artwork/" + tag + ".png",
                                 overwrite=False)
            if not isinstance(kra, dict) or not isinstance(png, dict):
                raise TaskError("Bridge did not confirm saved KRA and PNG")
            paths = (kra.get("path"), png.get("path"))
            if not all(isinstance(p, str) and Path(p).is_file() for p in paths):
                raise TaskError("Bridge did not return two real native artifacts")
        except Exception:
            # The KRA may have been saved despite a lost reply. The manifest
            # remains export_unknown; no automatic second save/export.
            raise
        # The full-composition stage previews are real Krita pixel snapshots.
        # They are collected by run ID from the owned Bridge output sandbox.
        compiled = json.loads(
            (self.root / "compiled-scene.json").read_text(encoding="utf-8")
        )
        stage_names = compiled.get("stage_preview_paths", [])
        if stage_names:
            info = client.request("status")
            if not isinstance(info, dict) or not info.get("output_dir"):
                raise TaskError("Bridge output directory unavailable for stage collection")
            native_root = Path(info["output_dir"]).resolve()
            dest = self.root / "stages"
            dest.mkdir(exist_ok=True)
            stage_records = {}
            from PIL import Image
            for filename in stage_names:
                source = (native_root / filename).resolve()
                if (native_root not in source.parents or not source.is_file()
                        or source.suffix.lower() != ".png"):
                    raise TaskError("Native stage preview missing or escaped its sandbox")
                if source.stat().st_size > 256 * 1024 * 1024:
                    raise TaskError("Native stage preview too large")
                with Image.open(source) as im:
                    im.verify()
                target = dest / Path(filename).name
                if target.exists():
                    raise FileExistsError("Stage evidence already exists")
                shutil.copy2(source, target)
                if _sha(target) != _sha(source):
                    raise TaskError("Native stage preview copy changed")
                stage_records[target.name] = {
                    "path": str(target.relative_to(self.root)),
                    "sha256": _sha(target),
                }
            record["artifacts"]["stage_previews"] = stage_records
        record["status"] = "awaiting_export"
        self._save(record, "native_export_both_confirmed")
        return self.record_artwork(*paths)

    def record_artwork(self, kra_path, png_path):
        """Archive real native artifacts as immutable versioned files."""
        record = self.read()
        self._expect(record, "awaiting_export")
        from PIL import Image
        import io
        source_kra = Path(kra_path).expanduser().resolve()
        source_png = Path(png_path).expanduser().resolve()
        if not source_kra.is_file() or not source_png.is_file():
            raise TaskError("Actual native KRA and PNG are both required")
        if source_kra.suffix.lower() != ".kra" or source_png.suffix.lower() != ".png":
            raise TaskError("Wrong native artifact types")
        if source_kra.stat().st_size > 2*1024*1024*1024 or source_png.stat().st_size > 256*1024*1024:
            raise TaskError("Native artifact exceeds storage budget")
        try:
            with zipfile.ZipFile(source_kra) as archive:
                if "maindoc.xml" not in archive.namelist():
                    raise TaskError("KRA lacks the native document manifest")
                merged = archive.read("mergedimage.png")
            with Image.open(io.BytesIO(merged)) as a, Image.open(source_png) as b:
                if a.size != b.size or a.convert("RGBA").tobytes() != b.convert("RGBA").tobytes():
                    raise TaskError("KRA merged image differs from exported PNG")
        except (OSError, zipfile.BadZipFile, KeyError) as exc:
            raise TaskError("Native KRA or PNG unreadable") from exc
        version = record["version"] + 1
        name = "v{:02d}".format(version)
        dest = self.root / "versions"
        dest.mkdir(exist_ok=True)
        copy_kra, copy_png = dest / (name + ".kra"), dest / (name + ".png")
        if copy_kra.exists() or copy_png.exists():
            raise FileExistsError("Versioned artwork may not be overwritten")
        shutil.copy2(source_kra, copy_kra)
        shutil.copy2(source_png, copy_png)
        if _sha(copy_kra) != _sha(source_kra) or _sha(copy_png) != _sha(source_png):
            raise TaskError("Native artwork changed during archive copy")
        record["version"] = version
        record["artifacts"]["latest"] = {
            "kra": str(copy_kra.relative_to(self.root)),
            "png": str(copy_png.relative_to(self.root)),
            "kra_sha256": _sha(copy_kra),
            "png_sha256": _sha(copy_png),
        }
        record["status"] = "awaiting_critique"
        self._save(record, "native_artwork_archived_" + name)
        return {"status": record["status"], "version": version,
                "files": record["artifacts"]["latest"]}

    def _current_png(self, record):
        latest = record["artifacts"].get("latest")
        if not isinstance(latest, dict):
            raise TaskError("No archived actual artwork")
        path = (self.root / latest["png"]).resolve()
        if self.root not in path.parents or _sha(path) != latest["png_sha256"]:
            raise TaskError("Archived native PNG changed")
        return path

    def critique(self, provider, reference=None, max_rounds=3):
        record = self.read()
        self._expect(record, "awaiting_critique")
        path = self._current_png(record)
        rounds = record.get("critique_rounds", 0) + 1
        result = critique(
            json.loads((self.root / "scene-plan-v3.json").read_text(encoding="utf-8")),
            path, provider, reference, max_round=max_rounds, round_index=rounds,
        )
        folder = self.root / "critiques"
        folder.mkdir(exist_ok=True)
        location = folder / ("critique-{:02d}.json".format(rounds))
        _write_new(location, result)
        record["critique_rounds"] = rounds
        record["artifacts"]["latest_critique"] = {
            "path": str(location.relative_to(self.root)),
            "sha256": _sha(location),
        }
        record["status"] = {
            "pass": "ready_for_delivery",
            "needs_revision": "awaiting_revision_proposal",
            "insufficient_evidence": "review_blocked",
        }[result["decision"]]
        self._save(record, "creative_critique_" + result["decision"])
        return {"status": record["status"], "critique": result}

    def propose_revision(self, object_id, provider=None, candidate=None, issue_id=None):
        record = self.read()
        self._expect(record, "awaiting_revision_proposal")
        if (provider is None) == (candidate is None):
            raise TaskError("Provide exactly one revision provider or candidate")
        scene = json.loads((self.root / "scene-plan-v3.json").read_text(encoding="utf-8"))
        critique_ref = record["artifacts"]["latest_critique"]
        path = (self.root / critique_ref["path"]).resolve()
        if _sha(path) != critique_ref["sha256"]:
            raise TaskError("Critique changed after review")
        review = json.loads(path.read_text(encoding="utf-8"))
        image = self._current_png(record)
        if provider is not None:
            revision = plan_revision(scene, review, image, object_id, provider)
        else:
            if not isinstance(issue_id, str):
                raise TaskError("Manual revision requires the reviewed issue ID")
            revision = validate_revision(scene, review, image, candidate, issue_id)
        location = self.root / ("revision-{:02d}.json".format(record["version"]))
        _write_new(location, revision)
        record["artifacts"]["revision"] = {
            "path": location.name, "sha256": _sha(location),
        }
        record["status"] = "revision_proposed"
        self._save(record, "revision_plan_proposed")
        return {"status": record["status"], "revision_sha256": revision["sha256"],
                "target_object": revision["object_id"], "strokes": len(revision["steps"]) - 2}

    def approve_revision(self, confirm=False):
        if confirm is not True:
            raise TaskError("Explicit revision approval required")
        record = self.read()
        self._expect(record, "revision_proposed")
        item = record["artifacts"]["revision"]
        path = (self.root / item["path"]).resolve()
        if _sha(path) != item["sha256"]:
            raise TaskError("Revision plan changed before approval")
        record["status"] = "revision_approved"
        self._save(record, "revision_approved_by_user")
        return {"status": record["status"], "revision_sha256": item["sha256"]}

    def apply_revision(self, client, confirm=False, ledger_directory=None,
                       graph_sha256=None):
        if confirm is not True:
            raise TaskError("Explicit native revision execution approval required")
        record = self.read()
        self._expect(record, "revision_approved")
        ref = record["artifacts"]["revision"]
        path = (self.root / ref["path"]).resolve()
        if _sha(path) != ref["sha256"]:
            raise TaskError("Revision plan changed after approval")
        revision = json.loads(path.read_text(encoding="utf-8"))
        scene = json.loads((self.root / "scene-plan-v3.json").read_text(encoding="utf-8"))
        artwork = self._current_png(record)
        record["status"] = "revision_unknown"
        self._save(record, "native_revision_submission_intent")
        try:
            result = execute_revision(
                client, revision, scene, artwork,
                ledger_directory or self.root / "revision-ledgers",
                confirm=True, current_graph_sha256=graph_sha256,
            )
        except Exception as exc:
            record["status"] = "unknown_needs_review"
            record["review_block_reason"] = str(exc)
            self._save(record, "native_revision_uncertain")
            raise
        record["revision_result"] = result
        record["status"] = (
            "awaiting_export" if result.get("state") == "completed" else "unknown_needs_review"
        )
        self._save(record, "native_revision_" + result.get("state", "unknown"))
        return {"status": record["status"], "result": result}

    def prepare_delivery(self):
        record = self.read()
        self._expect(record, "ready_for_delivery")
        self._current_png(record)
        latest = record["artifacts"]["latest"]
        target_kra, target_png = self.root / "artwork.kra", self.root / "artwork.png"
        if target_kra.exists() or target_png.exists():
            raise FileExistsError("Final artwork targets already exist; never overwrite")
        source_kra = (self.root / latest["kra"]).resolve()
        if _sha(source_kra) != latest["kra_sha256"]:
            raise TaskError("Archived KRA changed before delivery")
        shutil.copy2(source_kra, target_kra)
        shutil.copy2(self.root / latest["png"], target_png)
        record["status"] = "delivery_prepared"
        record["delivery"] = {
            "kra_sha256": _sha(target_kra), "png_sha256": _sha(target_png),
            "native_artwork_present": True,
            "independent_visual_review": "pending",
            "human_review": "pending",
            "full_artwork_accepted": False,
        }
        self._save(record, "delivery_prepared_not_accepted")
        return {"status": record["status"], "delivery": record["delivery"]}
