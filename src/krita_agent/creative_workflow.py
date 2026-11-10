"""Auditable multi-stage creative workflow with explicit side-effect boundaries.

No phase auto-replays native drawing. An interrupted paint, export or revision
is UNKNOWN and must be inspected manually; work-in-progress artifacts are kept.
"""
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .artifact_integrity import export_integrity, reopen_stability
from .creative_director import compile_approved, propose, validate_brief
from .generalist_director import propose_generalist, compile_approved_generalist
from .scene_v4 import SCHEMA as SCHEMA_V4, validate_scene_v4, lower_scene_v4
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
    "unknown_needs_review", "awaiting_reopen", "reopen_unknown",
    "awaiting_stage_approval",
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

    def plan(self, provider=None, candidate=None, reference=None,
             profile_directory=None, build=None, generalist=False):
        """Plan a legacy ScenePlan v3 or an explicitly selected generalist v4.

        v4 is lowered to v3 for the existing reviewed pixel-critic and revision
        contracts. Both immutable sources are recorded and hash-bound.
        """
        record = self.read()
        self._expect(record, "initialized")
        if (provider is None) == (candidate is None):
            raise TaskError("Choose exactly one provider or manually supplied scene")
        v4_scene = None
        generalist_proposal = None
        if provider is not None and generalist:
            generalist_proposal = propose_generalist(record["brief"], provider, reference)
            v4_scene = generalist_proposal["scene_v4"]
            scene, _ = lower_scene_v4(v4_scene)
            proposal = {
                "schema": "krita-agent-creative-proposal/1", "scene": scene,
                "scene_sha256": digest(scene),
                "provider_model": generalist_proposal["provider_model"],
                "approval": "required", "side_effects": "none",
            }
        elif provider is not None:
            proposal = propose(record["brief"], provider, reference)
        elif isinstance(candidate, dict) and candidate.get("schema") == SCHEMA_V4:
            v4_scene = validate_scene_v4(candidate)
            scene, _ = lower_scene_v4(v4_scene)
            proposal = {
                "schema": "krita-agent-creative-proposal/1", "scene": scene,
                "scene_sha256": digest(scene), "provider_model": "human_supplied",
                "approval": "required", "side_effects": "none",
            }
            generalist_proposal = {
                "schema": "krita-agent-generalist-proposal/1",
                "scene_v4": v4_scene, "scene_v4_sha256": digest(v4_scene),
                "provider_model": "human_supplied", "approval": "required",
            }
        else:
            if generalist:
                raise TaskError("Generalist option requires a v4 candidate or provider")
            scene = validate_scene(candidate)
            proposal = {
                "schema": "krita-agent-creative-proposal/1", "scene": scene,
                "scene_sha256": digest(scene), "provider_model": "human_supplied",
                "approval": "required", "side_effects": "none",
            }
        if (proposal["scene"]["document"]["width"],
                proposal["scene"]["document"]["height"]) != (
                record["brief"]["width"], record["brief"]["height"]):
            raise TaskError("Scene differs from the approved canvas dimensions")
        preview_prefix = "r5-runs/" + record["id"]
        if v4_scene is None:
            compiled = compile_approved(
                proposal, profile_directory, build, preview_prefix=preview_prefix)
        else:
            compiled = compile_approved_generalist(
                generalist_proposal, profile_directory, build,
                preview_prefix=preview_prefix)
            if compiled["source_sha256"] != digest(proposal["scene"]):
                raise TaskError("Generalist lowering does not match approved v3 source")
            _write_new(self.root / "scene-plan-v4.json", v4_scene)
            _write_new(self.root / "generalist-proposal.json", generalist_proposal)
            record["artifacts"]["scene_v4"] = {
                "path": "scene-plan-v4.json",
                "sha256": _sha(self.root / "scene-plan-v4.json"),
            }
            record["artifacts"]["generalist_proposal"] = {
                "path": "generalist-proposal.json",
                "sha256": _sha(self.root / "generalist-proposal.json"),
            }
            record["staged"] = {"total": len(compiled["stage_spans"]),
                                "next_stage": 0, "completed": []}
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
        self._save(record, "generalist_plan_proposed" if v4_scene else "plan_proposed")
        result = {"status": record["status"],
                  "plan_sha256": compiled["native_steps_sha256"],
                  "objects": len(compiled["objects"]),
                  "native_steps": len(compiled["steps"]),
                  "brush_diagnostics": compiled.get("brush_diagnostics")}
        if v4_scene is not None:
            result["stage_spans"] = compiled["stage_spans"]
            result["subjects"] = len(v4_scene["subjects"])
        return result

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
        if "staged" in record:
            self._verified_staged_plan(record)
        record["status"] = "plan_approved"
        self._save(record, "plan_approved_by_user")
        return {"status": record["status"], "plan_sha256": compiled["native_steps_sha256"]}

    def paint(self, client, ledger_directory=None, batch_steps=120):
        record = self.read()
        self._expect(record, "plan_approved")
        if "staged" in record:
            raise TaskError("Generalist v4 requires paint-stage --confirm at each phase")
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

    def _verified_staged_plan(self, record):
        """Re-bind every stage to both immutable source scenes and native steps."""
        if "staged" not in record or "scene_v4" not in record["artifacts"]:
            raise TaskError("No approved generalist stage plan")
        for key in ("compiled", "scene", "scene_v4", "generalist_proposal"):
            entry = record["artifacts"].get(key)
            if not isinstance(entry, dict):
                raise TaskError("Missing generalist plan artifact: " + key)
            path = (self.root / entry.get("path", "")).resolve()
            if self.root not in path.parents or not path.is_file() or _sha(path) != entry.get("sha256"):
                raise TaskError("Generalist source artifact changed: " + key)
        compiled = json.loads((self.root / "compiled-scene.json").read_text(encoding="utf-8"))
        source = json.loads((self.root / "scene-plan-v4.json").read_text(encoding="utf-8"))
        proposal = json.loads((self.root / "generalist-proposal.json").read_text(encoding="utf-8"))
        v4 = validate_scene_v4(source)
        lowered, _ = lower_scene_v4(v4)
        if (proposal.get("scene_v4_sha256") != digest(v4)
                or digest(proposal.get("scene_v4")) != digest(v4)
                or compiled.get("source_v4_sha256") != digest(v4)
                or digest(lowered) != compiled.get("source_sha256")
                or digest(lowered) != digest(json.loads(
                    (self.root / "scene-plan-v3.json").read_text(encoding="utf-8")))):
            raise TaskError("Approved generalist stage sources do not match")
        steps = compiled.get("steps")
        spans = compiled.get("stage_spans")
        if (not isinstance(steps, list) or not isinstance(spans, list)
                or len(spans) != record["staged"].get("total")
                or len(spans) != len(v4["stages"])
                or compiled.get("native_steps_sha256") != digest(steps)):
            raise TaskError("Compiled generalist stage count or hash mismatch")
        cursor = 0
        for idx, stage in enumerate(spans):
            if (stage.get("index") != idx
                    or stage.get("id") != v4["stages"][idx]["id"]
                    or stage.get("start") != cursor
                    or type(stage.get("stop")) is not int
                    or not cursor < stage["stop"] <= len(steps)
                    or stage.get("steps_sha256") != digest(steps[cursor:stage["stop"]])):
                raise TaskError("Compiled generalist stage boundary changed")
            cursor = stage["stop"]
        if cursor != len(steps):
            raise TaskError("Compiled generalist stage tail is unbound")
        return compiled

    @staticmethod
    def _stage_live_identity(client, document):
        """Conservative active document and layer-graph fingerprint.

        The fingerprint rejects wrong/changed documents; it does not claim
        full pixel-integrity or substitute for fresh-KRA reopen acceptance.
        """
        docs = client.request("document.list")
        if not isinstance(docs, list):
            raise TaskError("Cannot identify the active Krita document")
        active = [row for row in docs if isinstance(row, dict)
                  and row.get("active") is True]
        if len(active) != 1:
            raise TaskError("Expected exactly one active Krita document")
        row = active[0]
        if (row.get("name") != document["name"]
                or row.get("width") != document["width"]
                or row.get("height") != document["height"]):
            raise TaskError("Active Krita document differs from staged plan")
        graph = client.request("layer.tree")
        if not isinstance(graph, (dict, list)):
            raise TaskError("Native layer graph unavailable for stage approval")
        return {
            "document": {
                "index": row.get("index"), "name": row["name"],
                "width": row["width"], "height": row["height"],
                "file_path": row.get("file_path"),
                "color_model": row.get("color_model"),
                "color_depth": row.get("color_depth"),
                "color_profile": row.get("color_profile"),
            },
            "layer_graph_sha256": digest(graph),
        }

    def paint_stage(self, client, confirm=False, ledger_directory=None,
                    batch_steps=120):
        """One user-confirmed stage per invocation; never auto-submit the next."""
        if confirm is not True:
            raise TaskError("Each native painting stage requires explicit --confirm")
        record = self.read()
        self._expect(record, "plan_approved", "awaiting_stage_approval")
        compiled = self._verified_staged_plan(record)
        state = record["staged"]
        index = state.get("next_stage")
        if type(index) is not int or not 0 <= index < state["total"]:
            raise TaskError("Generalist stage cursor is invalid")
        if index > 0:
            expected = record.get("stage_live")
            current = self._stage_live_identity(client, compiled["document"])
            if expected != current:
                raise TaskError("Active Krita document/layers changed since last stage")
        stage = compiled["stage_spans"][index]
        segment = compiled["steps"][stage["start"]:stage["stop"]]
        if digest(segment) != stage["steps_sha256"]:
            raise TaskError("Generalist stage instructions changed")
        record["status"] = "painting_unknown"
        record["active_stage"] = index
        self._save(record, "native_stage_%02d_submission_intent" % (index+1))
        try:
            result = run_longjob(
                client, {"steps": segment},
                ledger_directory or self.root / "stage-ledgers",
                batch_steps=batch_steps,
            )
            if result.get("state") != "completed":
                record["stage_result"] = result
                record["status"] = "unknown_needs_review"
                self._save(record, "native_stage_%02d_uncertain" % (index+1))
                return {"status": record["status"], "stage": index+1, "native": result}
            fingerprint = self._stage_live_identity(client, compiled["document"])
        except Exception as exc:
            record["status"] = "unknown_needs_review"
            record["stage_error"] = str(exc)
            self._save(record, "native_stage_%02d_uncertain" % (index+1))
            raise
        state["completed"].append({
            "stage_index": index, "id": stage["id"],
            "steps_sha256": stage["steps_sha256"], "native": result,
        })
        state["next_stage"] = index+1
        record["stage_live"] = fingerprint
        record.pop("active_stage", None)
        record["status"] = ("awaiting_export" if index+1 == state["total"]
                            else "awaiting_stage_approval")
        self._save(record, "native_stage_%02d_completed" % (index+1))
        return {"status": record["status"], "stage": index+1,
                "total_stages": state["total"], "native": result,
                "next_stage_requires_approval": index+1 < state["total"]}

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
        # Archive the original native pair FIRST, even when stage evidence or
        # a subsequent fresh reopen fails. Never lose a mismatching candidate.
        record["status"] = "awaiting_export"
        self._save(record, "native_export_both_confirmed")
        archived = self.record_artwork(*paths)
        record = self.read()
        # The full-composition stage previews are real Krita pixel snapshots.
        # They are collected by run ID from the owned Bridge output sandbox.
        compiled = json.loads(
            (self.root / "compiled-scene.json").read_text(encoding="utf-8")
        )
        stage_names = compiled.get("stage_preview_paths", [])
        archived_stages = record["artifacts"].get("stage_previews")
        if archived_stages is not None:
            if set(archived_stages) != {Path(name).name for name in stage_names}:
                raise TaskError("Archived stage evidence does not match the compiled plan")
            for name, entry in archived_stages.items():
                target = self.root / "stages" / name
                if (str(target.relative_to(self.root)) != entry["path"]
                        or not target.is_file() or _sha(target) != entry["sha256"]):
                    raise TaskError("Archived stage evidence changed")
        elif stage_names:
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
        self._save(record, "native_stage_evidence_archived")
        if archived["status"] != "awaiting_reopen":
            return archived  # Preserve stage evidence even if the export itself failed.
        return self.verify_reopen(client)

    def record_artwork(self, kra_path, png_path, confirm_new_version=False):
        """Always archive the original native KRA/PNG, including failed exports.

        An independently repaired KRA is a NEW version, never an in-place patch.
        A manually supplied pair is pending until Krita really reopens a fresh copy.
        """
        record = self.read()
        if record["status"] == "review_blocked":
            if confirm_new_version is not True:
                raise TaskError("A repaired candidate requires explicit new-version approval")
        else:
            self._expect(record, "awaiting_export")
            if confirm_new_version:
                raise TaskError("Repair-version approval is only valid for a blocked version")
        source_kra = Path(kra_path).expanduser().resolve()
        source_png = Path(png_path).expanduser().resolve()
        if not source_kra.is_file() or not source_png.is_file():
            raise TaskError("Actual native KRA and PNG are both required")
        if source_kra.suffix.lower() != ".kra" or source_png.suffix.lower() != ".png":
            raise TaskError("Wrong native artifact types")
        if source_kra.stat().st_size > 2*1024*1024*1024 or source_png.stat().st_size > 256*1024*1024:
            raise TaskError("Native artifact exceeds storage budget")
        previous = record["artifacts"].get("latest")
        if confirm_new_version and previous and (
                _sha(source_kra) == previous.get("kra_sha256")
                and _sha(source_png) == previous.get("png_sha256")):
            raise TaskError("Repaired candidate is byte-identical to the rejected version")
        version = record["version"] + 1
        name = "v{:02d}".format(version)
        dest = self.root / "versions"
        dest.mkdir(exist_ok=True)
        copy_kra, copy_png = dest / (name + ".kra"), dest / (name + ".png")
        report_path = dest / (name + "-integrity.json")
        if any(path.exists() for path in (copy_kra, copy_png, report_path)):
            raise FileExistsError("Versioned artwork may not be overwritten")
        # Copy first: even an invalid/corrupt KRA must survive technical rejection.
        shutil.copy2(source_kra, copy_kra)
        shutil.copy2(source_png, copy_png)
        if _sha(copy_kra) != _sha(source_kra) or _sha(copy_png) != _sha(source_png):
            raise TaskError("Native artwork changed during archive copy")
        export = export_integrity(copy_kra, copy_png)
        report = {
            "schema": "krita-agent-artifact-integrity/1",
            "version": version, "export_integrity": export,
            "reopen_stability": {"status": "pending", "reason": "Fresh Krita reopen required"},
            "parent_version": (version - 1) if confirm_new_version else None,
        }
        _write_new(report_path, report)
        record["version"] = version
        record["artifacts"].pop("latest_critique", None)
        record["artifacts"].pop("revision", None)
        record["artifacts"]["latest"] = {
            "kra": str(copy_kra.relative_to(self.root)),
            "png": str(copy_png.relative_to(self.root)),
            "kra_sha256": _sha(copy_kra),
            "png_sha256": _sha(copy_png),
            "integrity": str(report_path.relative_to(self.root)),
            "integrity_sha256": _sha(report_path),
            "export_integrity": export["status"],
            "reopen_stability": "pending",
        }
        if export["status"] != "pass":
            record["status"] = "review_blocked"
            record["review_block_reason"] = "Export Integrity failed; original KRA/PNG retained"
        else:
            record["status"] = "awaiting_reopen"
            record.pop("review_block_reason", None)
        self._save(record, "native_artwork_archived_" + name)
        return {"status": record["status"], "version": version,
                "files": record["artifacts"]["latest"], "export_integrity": export}

    def verify_reopen(self, client):
        """Open a UNIQUE fresh copy in Krita, export it, and compare exact pixels.

        The intent is durable before document.open. An uncertain Bridge response
        is never replayed, and the original active document must be restored.
        """
        record = self.read()
        self._expect(record, "awaiting_reopen")
        latest = record["artifacts"]["latest"]
        source_kra = (self.root / latest["kra"]).resolve()
        source_png = (self.root / latest["png"]).resolve()
        if (self.root not in source_kra.parents or self.root not in source_png.parents
                or _sha(source_kra) != latest["kra_sha256"]
                or _sha(source_png) != latest["png_sha256"]):
            raise TaskError("Archived KRA/PNG changed before fresh-reopen inspection")
        report_path = (self.root / latest["integrity"]).resolve()
        if self.root not in report_path.parents or _sha(report_path) != latest["integrity_sha256"]:
            raise TaskError("Integrity evidence changed before fresh-reopen inspection")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report["export_integrity"]["status"] != "pass" or report["reopen_stability"]["status"] != "pending":
            raise TaskError("Only export-clean, not-yet-reopened versions may be verified")
        status = client.request("status")
        documents = client.request("document.list")
        if not isinstance(status, dict) or not status.get("output_dir"):
            raise TaskError("Bridge output sandbox unavailable")
        if not isinstance(documents, list) or sum(row.get("active") is True for row in documents
                                                 if isinstance(row, dict)) != 1:
            raise TaskError("Unable to identify original active Krita document")
        original = next(row for row in documents if row.get("active") is True)
        native_root = Path(status["output_dir"]).resolve()
        if not native_root.is_dir():
            raise TaskError("Bridge output sandbox does not exist")
        unique = uuid.uuid4().hex
        relative = Path("r5-reopen") / record["id"] / ("v{:02d}-".format(record["version"]) + unique)
        original_copy = native_root / (str(relative) + ".kra")
        reopened_png = native_root / (str(relative) + ".png")
        archived_reopen = self.root / "versions" / ("v{:02d}-reopened.png".format(record["version"]))
        if any(path.exists() for path in (original_copy, reopened_png, archived_reopen)):
            raise FileExistsError("Fresh-reopen evidence target already exists")
        original_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_kra, original_copy)
        if _sha(original_copy) != latest["kra_sha256"]:
            raise TaskError("Fresh KRA copy changed before opening")
        record["status"] = "reopen_unknown"
        self._save(record, "native_reopen_submission_intent")
        try:
            opened = client.request("document.open", path=str(relative) + ".kra")
            if not isinstance(opened, dict) or opened.get("opened") != str(original_copy):
                raise TaskError("Bridge did not confirm opening the exact fresh KRA")
            new_index = opened.get("index")
            if type(new_index) is not int or new_index in [row.get("index") for row in documents]:
                raise TaskError("Bridge did not identify a unique newly opened document")
            client.request("document.activate", index=new_index)
            active = client.request("document.list")
            matches = [row for row in active if isinstance(row, dict)
                       and row.get("index") == new_index and row.get("active") is True
                       and Path(row.get("file_path") or "").resolve() == original_copy]
            if len(matches) != 1 or len(active) != len(documents) + 1:
                raise TaskError("Freshly opened KRA is not uniquely active")
            exported = client.request("document.export", path=str(relative) + ".png",
                                      overwrite=False)
            if not isinstance(exported, dict) or exported.get("path") != str(reopened_png):
                raise TaskError("Bridge did not confirm the fresh-KRA PNG")
            if not reopened_png.is_file():
                raise TaskError("Fresh-KRA export is missing")
            # Do not close/activate based on names: use exact path and index.
            current = client.request("document.list")
            if not any(row.get("index") == new_index and Path(row.get("file_path") or "").resolve() == original_copy
                       for row in current if isinstance(row, dict)):
                raise TaskError("Fresh-KRA identity changed before close")
            client.request("document.close", index=new_index, confirm=True)
            client.request("document.activate", index=original["index"])
            restored = client.request("document.list")
            if not any(row.get("index") == original["index"] and row.get("active") is True
                       and row.get("name") == original["name"]
                       and Path(row.get("file_path") or "").resolve() == Path(original.get("file_path") or "").resolve()
                       for row in restored if isinstance(row, dict)):
                raise TaskError("Original Krita document was not restored")
            shutil.copy2(reopened_png, archived_reopen)
            if _sha(archived_reopen) != _sha(reopened_png):
                raise TaskError("Reopened PNG changed during archive copy")
        except Exception:
            # Raw KRA, initial PNG, fresh copy and any native export are retained.
            record = self.read()
            record["status"] = "unknown_needs_review"
            record["review_block_reason"] = (
                "Fresh reopen/export/restore was uncertain; inspect native documents "
                "and preserved r5-reopen evidence before any retry"
            )
            self._save(record, "native_reopen_uncertain")
            raise
        stability = reopen_stability(source_png, archived_reopen, latest["kra_sha256"])
        report["reopen_stability"] = stability
        report["reopened_png"] = {
            "path": str(archived_reopen.relative_to(self.root)),
            "sha256": _sha(archived_reopen),
            "method": "fresh-copy-krita-document.open-document.export",
            "native_copy": str(original_copy),
            "native_export": str(reopened_png),
            "native_reopened_document_color": {
                "model": opened.get("color_model"),
                "depth": opened.get("color_depth"),
                "profile": opened.get("color_profile"),
            },
            "native_original_document_color": {
                "model": original.get("color_model"),
                "depth": original.get("color_depth"),
                "profile": original.get("color_profile"),
            },
        }
        # Integrity reports are versioned and immutable: new evidence replaces
        # only a pending report, using a uniquely named second file.
        final_report = report_path.with_name(report_path.stem + "-verified.json")
        _write_new(final_report, report)
        latest["integrity"] = str(final_report.relative_to(self.root))
        latest["integrity_sha256"] = _sha(final_report)
        latest["reopened_png"] = report["reopened_png"]["path"]
        latest["reopened_png_sha256"] = report["reopened_png"]["sha256"]
        latest["reopen_stability"] = stability["status"]
        record["status"] = "awaiting_critique" if stability["status"] == "pass" else "review_blocked"
        if stability["status"] != "pass":
            record["review_block_reason"] = "Reopen Stability failed; preserve and review this version"
        self._save(record, "native_reopen_" + stability["status"])
        return {"status": record["status"], "version": record["version"],
                "files": latest, "reopen_stability": stability}

    def _verified_integrity(self, record):
        """Recompute both strict gates from retained immutable version artifacts."""
        latest = record["artifacts"].get("latest", {})
        required = ("kra", "png", "reopened_png", "integrity", "kra_sha256",
                    "png_sha256", "reopened_png_sha256", "integrity_sha256")
        if any(key not in latest for key in required):
            raise TaskError("Export/reopen evidence is incomplete")
        paths = {key: (self.root / latest[key]).resolve()
                 for key in ("kra", "png", "reopened_png", "integrity")}
        for key, path in paths.items():
            if (self.root not in path.parents or not path.is_file()
                    or _sha(path) != latest[key + "_sha256"]):
                raise TaskError("Archived " + key + " evidence changed")
        report = json.loads(paths["integrity"].read_text(encoding="utf-8"))
        exported = export_integrity(paths["kra"], paths["png"])
        reopened = reopen_stability(paths["png"], paths["reopened_png"],
                                     latest["kra_sha256"])
        if (report.get("export_integrity") != exported
                or report.get("reopen_stability") != reopened
                or exported["status"] != "pass" or reopened["status"] != "pass"):
            raise TaskError("Export Integrity / Reopen Stability is not strictly verified")
        entry = report.get("reopened_png", {})
        if entry.get("path") != latest["reopened_png"] or entry.get("sha256") != latest["reopened_png_sha256"]:
            raise TaskError("Reopen evidence is not bound to the current version")
        return report, paths

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
        self._verified_integrity(record)
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
        report, verified = self._verified_integrity(record)
        latest = record["artifacts"]["latest"]
        targets = {
            "kra": self.root / "artwork.kra",
            "png": self.root / "artwork.png",
            "reopened_png": self.root / "reopened.png",
            "integrity": self.root / "reopen-evidence.json",
        }
        if any(path.exists() for path in targets.values()):
            raise FileExistsError("Final artwork/evidence targets already exist; never overwrite")
        for key, target in targets.items():
            shutil.copy2(verified[key], target)
            if _sha(target) != latest[key + "_sha256"]:
                raise TaskError("Delivery copy changed: " + key)
        record["status"] = "delivery_prepared"
        record["delivery"] = {
            "kra_sha256": _sha(targets["kra"]), "png_sha256": _sha(targets["png"]),
            "reopened_png_sha256": _sha(targets["reopened_png"]),
            "reopen_evidence_sha256": _sha(targets["integrity"]),
            "export_integrity": report["export_integrity"]["status"],
            "reopen_stability": report["reopen_stability"]["status"],
            "native_artwork_present": True,
            "independent_visual_review": "pending",
            "human_review": "pending",
            "full_artwork_accepted": False,
        }
        self._save(record, "delivery_prepared_not_accepted")
        return {"status": record["status"], "delivery": record["delivery"]}
